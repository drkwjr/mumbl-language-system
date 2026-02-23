"""Main service entrypoint for radio ingestion"""

import asyncio
import json
import os
import re
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import structlog
from mumbl_storage.db import DatabaseConfig, get_connection
from mumbl_storage.repositories import (
    PipelineEventRepository,
    SegmentLanguageVerificationRepository,
)
from psycopg.rows import dict_row
from radio_ingestion.capture import CaptureScheduler, StreamRecorder
from radio_ingestion.config import RadioIngestionConfig, get_config
from radio_ingestion.discovery.radio_browser import discover_stations
from radio_ingestion.lid import create_aggregator, create_fusion, create_lid_model
from radio_ingestion.lid.llm_language_classifier import LLMLanguageClassifier
from radio_ingestion.orchestration.scheduler import BackpressureController, TaskScheduler
from radio_ingestion.orchestration.task_queue import PipelineProcessor, TaskQueue
from radio_ingestion.prefilter import WindowExtractor
from radio_ingestion.storage.radio_repositories import (
    CaptureTargetRepository,
    LanguageLabelMapRepository,
    RadioSegmentRepository,
    RadioShardRepository,
    RadioSourceRepository,
    RadioStationDaypartRepository,
    RadioStationHourlyRepository,
)

logger = structlog.get_logger(__name__)

HARD_FAILURE_KINDS = {
    "not_found",
    "forbidden",
    "unauthorized",
    "dns",
}


def _daypart_from_hour(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _resolve_listening_timezone(
    station_timezone: Optional[str],
    strategy: str,
    fallback_timezone: Optional[str],
):
    if strategy == "local":
        if fallback_timezone:
            return ZoneInfo(fallback_timezone), fallback_timezone
        local_tz = datetime.now().astimezone().tzinfo
        return (local_tz or timezone.utc), "local"

    if station_timezone:
        try:
            return ZoneInfo(station_timezone), station_timezone
        except Exception:
            pass

    if fallback_timezone:
        return ZoneInfo(fallback_timezone), fallback_timezone

    local_tz = datetime.now().astimezone().tzinfo
    return (local_tz or timezone.utc), "local"


def _should_skip_capture(
    source: Dict[str, Any],
    cooldown_minutes: int,
    now: datetime,
) -> Optional[str]:
    if cooldown_minutes <= 0:
        return None

    failures = source.get("health_consecutive_failures") or 0
    status = source.get("health_status")
    last_failure_at = source.get("health_last_failure_at")
    last_check = source.get("last_check")

    if failures <= 0 and status != "down":
        return None

    last_event = last_failure_at or (last_check if status == "down" else None)
    if not isinstance(last_event, datetime):
        return None

    elapsed = now - last_event
    if elapsed >= timedelta(minutes=cooldown_minutes):
        return None

    remaining = timedelta(minutes=cooldown_minutes) - elapsed
    minutes_left = max(1, int(remaining.total_seconds() // 60))
    return f"cooldown {minutes_left}m remaining"


def _capture_priority(source: Dict[str, Any], now: datetime) -> float:
    score = 0.0
    status = source.get("health_status") or "unknown"
    if status == "down":
        score -= 50.0
    elif status == "degraded":
        score -= 10.0

    last_success = source.get("last_successful_capture")
    if isinstance(last_success, datetime):
        age_hours = (now - last_success).total_seconds() / 3600.0
        score += min(age_hours, 72.0)
    else:
        score += 72.0

    failures = source.get("health_consecutive_failures") or 0
    score -= float(failures) * 2.0
    return score


def _attention_score(
    source: Dict[str, Any],
    stats: Optional[Dict[str, Any]],
    now: datetime,
) -> float:
    score = _capture_priority(source, now)
    if stats:
        speech_ratio = stats.get("speech_ratio") or 0.0
        avg_confidence = stats.get("avg_confidence") or 0.0
        score += float(speech_ratio) * 20.0
        score += float(avg_confidence) * 10.0
    return score


def _should_quarantine(
    conn,
    source_id: int,
    window_hours: int,
    threshold: int,
) -> bool:
    if threshold <= 0:
        return False
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM pipeline_events
            WHERE created_at >= %s
              AND source_id = %s
              AND stage = 'capture'
              AND event_type = 'capture_failed'
              AND (payload->>'error_kind') = ANY(%s)
            """,
            (window_start, source_id, list(HARD_FAILURE_KINDS)),
        )
        row = cur.fetchone()
    return int(row["total"] or 0) >= threshold


def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _normalize_stream_url(stream_url: Optional[str]) -> Optional[str]:
    if not stream_url:
        return None
    try:
        parsed = urlparse(stream_url)
    except Exception:
        return stream_url
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return base.rstrip("/")


def _canonical_key(source: Dict[str, Any]) -> str:
    normalized_stream = _normalize_stream_url(source.get("stream_url"))
    if normalized_stream:
        return f"stream:{normalized_stream}"
    homepage = source.get("homepage")
    domain = None
    if homepage:
        try:
            domain = urlparse(homepage).netloc.lower()
        except Exception:
            domain = None
    normalized_name = _normalize_name(source.get("name"))
    return f"site:{domain or 'unknown'}|name:{normalized_name}"


def _fetch_taxonomy(conn, country_code: Optional[str]) -> Dict[str, Any]:
    if not country_code:
        return {"languages": [], "dialects": []}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT iso639_3, iso639_1, name, family_code, countries
            FROM language_taxonomy
            WHERE countries @> %s
            """,
            (json.dumps([country_code]),),
        )
        languages = [dict(row) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT language_iso639_3, dialect_code, name, region
            FROM language_dialects
            WHERE language_iso639_3 IN (
                SELECT iso639_3
                FROM language_taxonomy
                WHERE countries @> %s
            )
            """,
            (json.dumps([country_code]),),
        )
        dialects = [dict(row) for row in cur.fetchall()]
    return {"languages": languages, "dialects": dialects}


class RadioIngestionService:
    """Main radio ingestion service"""

    def __init__(self, config: Optional[RadioIngestionConfig] = None):
        """
        Initialize service.

        Args:
            config: Configuration instance (uses get_config() if None)
        """
        self.config = config or get_config()
        self.running = False
        self.task_queue: Optional[TaskQueue] = None
        self.processor: Optional[PipelineProcessor] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.backpressure: Optional[BackpressureController] = None

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("Radio ingestion service initialized")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal", signal=signum)
        self.running = False

    async def refresh_stations(self):
        """Refresh stations from Radio Browser API"""
        logger.info("Starting station refresh")

        try:
            with get_connection() as conn:
                source_repo = RadioSourceRepository(conn)

                # Discover stations for configured countries/languages
                # For now, use a default set (could be configurable)
                discovered = discover_stations(
                    api_url=self.config.radio_browser_api,
                    country="SOM",  # Could be from config
                    limit=20,
                )

                if discovered:
                    source_ids = source_repo.insert_many(discovered)
                    logger.info(
                        "Station refresh complete",
                        discovered_count=len(discovered),
                        stored_count=len([sid for sid in source_ids if sid is not None]),
                    )
                else:
                    logger.warning("No stations discovered")

        except Exception as e:
            logger.error("Station refresh failed", error=str(e))

    async def capture_stations(self):
        """Capture audio from active stations"""
        logger.info("Starting station capture cycle")

        try:
            with get_connection() as conn:
                source_repo = RadioSourceRepository(conn)
                label_map_repo = LanguageLabelMapRepository(conn)
                shard_repo = RadioShardRepository(conn)
                segment_repo = RadioSegmentRepository(conn)
                capture_target_repo = CaptureTargetRepository(conn)
                daypart_repo = RadioStationDaypartRepository(conn)
                hourly_repo = RadioStationHourlyRepository(conn)
                pipeline_repo = PipelineEventRepository(conn)
                verification_repo = SegmentLanguageVerificationRepository(conn)

                label_map = label_map_repo.list_map()
                capture_countries = getattr(self.config, "capture_countries", None)
                capture_target = capture_target_repo.get_active()
                capture_languages = None
                if capture_target and capture_target.get("countries"):
                    capture_countries = capture_target["countries"]
                if capture_target and capture_target.get("languages"):
                    capture_languages = [
                        lang.strip().lower() for lang in capture_target.get("languages", []) if lang
                    ]
                iso3_to_iso2 = {
                    "GHA": "GH",
                    "SOM": "SO",
                }
                sources = []
                if capture_countries:
                    for country in capture_countries:
                        country_code = iso3_to_iso2.get(country, country)
                        sources.extend(source_repo.list_active(country=country_code))
                else:
                    sources = source_repo.list_active()

                if capture_languages:
                    sources = [
                        source
                        for source in sources
                        if (source.get("lang_hint") or "").lower() in capture_languages
                    ]

                if not sources:
                    logger.info("No active sources to capture")
                    return

                stats_map = hourly_repo.get_latest_for_sources([source["id"] for source in sources])
                now = datetime.now(timezone.utc)
                scored_sources = []
                for source in sources:
                    score = _attention_score(source, stats_map.get(source["id"]), now)
                    scored_sources.append((score, source))

                scored_sources.sort(key=lambda entry: entry[0], reverse=True)

                deduped_sources = []
                seen_keys = {}
                for score, source in scored_sources:
                    key = _canonical_key(source)
                    if key in seen_keys:
                        pipeline_repo.insert(
                            stage="capture",
                            event_type="capture_skipped",
                            status="warn",
                            source_id=source["id"],
                            message="Capture skipped: duplicate station",
                            payload={
                                "canonical_key": key,
                                "winner_source_id": seen_keys[key],
                                "attention_score": score,
                            },
                        )
                        continue
                    seen_keys[key] = source["id"]
                    deduped_sources.append((score, source))

                sources = [source for _, source in deduped_sources]

                if self.config.capture_source_limit:
                    sources = sources[: self.config.capture_source_limit]

                sources_by_id = {source["id"]: source for source in sources}

                # Get capture duration with backpressure
                capture_duration = (
                    self.backpressure.get_capture_duration()
                    if self.backpressure
                    else self.config.capture_duration
                )

                Path(self.config.capture_dir).mkdir(parents=True, exist_ok=True)
                recorder = StreamRecorder(
                    output_dir=self.config.capture_dir,
                    sample_rate=22050,
                    channels=1,
                    format="wav",
                )
                scheduler = CaptureScheduler(
                    recorder=recorder,
                    max_concurrent=self.config.max_concurrent_captures,
                )

                try:
                    extractor = WindowExtractor(
                        sample_rate=22050,
                        vad_aggressiveness=self.config.vad_aggressiveness,
                        music_threshold=self.config.music_threshold,
                        min_speech_duration=0.5,
                        max_window_duration=self.config.window_size,
                    )
                except Exception as e:
                    extractor = None
                    logger.error("Prefilter unavailable", error=str(e))

                try:
                    audio_lid = create_lid_model()
                except Exception as e:
                    audio_lid = None
                    logger.error("Audio LID unavailable", error=str(e))

                fusion = create_fusion()
                aggregator = create_aggregator()
                llm_classifier = None
                try:
                    if os.getenv("OPENAI_API_KEY"):
                        llm_classifier = LLMLanguageClassifier()
                except Exception as e:
                    logger.warning("LLM classifier unavailable", error=str(e))

                logger.info(
                    "Capture cycle", source_count=len(sources), capture_duration=capture_duration
                )

                for source in sources:
                    stream_url = source.get("stream_url")
                    if not stream_url:
                        continue
                    skip_reason = _should_skip_capture(
                        source,
                        self.config.failure_cooldown_minutes,
                        datetime.now(timezone.utc),
                    )
                    if skip_reason:
                        pipeline_repo.insert(
                            stage="capture",
                            event_type="capture_skipped",
                            status="warn",
                            source_id=source["id"],
                            message=f"Capture skipped: {skip_reason}",
                            payload={
                                "reason": skip_reason,
                                "health_status": source.get("health_status"),
                                "consecutive_failures": source.get("health_consecutive_failures"),
                            },
                        )
                        continue
                    await scheduler.schedule_capture(
                        source_id=source["id"],
                        stream_url=stream_url,
                        station_name=source.get("name", "unknown"),
                        duration=capture_duration,
                        max_retries=3,
                    )

                await scheduler.wait_for_completion(timeout=capture_duration + 30)

                for task in scheduler.get_failed_tasks():
                    source_repo.update_health(
                        task.source_id,
                        successful=False,
                        error_message=task.error_detail or task.error,
                        max_consecutive_failures=self.config.max_consecutive_failures,
                    )
                    pipeline_repo.insert(
                        stage="capture",
                        event_type="capture_failed",
                        status="error",
                        source_id=task.source_id,
                        duration_seconds=task.duration,
                        message=task.error,
                        payload={
                            "error_kind": task.error_kind,
                            "error_code": task.error_code,
                            "error_detail": task.error_detail,
                            "stream_url": task.stream_url,
                        },
                    )
                    if task.error_kind in HARD_FAILURE_KINDS:
                        if _should_quarantine(
                            conn,
                            task.source_id,
                            self.config.hard_failure_window_hours,
                            self.config.hard_failure_threshold,
                        ):
                            source_repo.mark_inactive(
                                task.source_id,
                                reason=f"hard_failures:{task.error_kind}",
                            )
                            pipeline_repo.insert(
                                stage="capture",
                                event_type="station_quarantined",
                                status="warn",
                                source_id=task.source_id,
                                message="Station marked inactive after hard failures",
                                payload={
                                    "error_kind": task.error_kind,
                                    "threshold": self.config.hard_failure_threshold,
                                    "window_hours": self.config.hard_failure_window_hours,
                                },
                            )

                for task in scheduler.get_completed_tasks():
                    source_repo.update_health(
                        task.source_id,
                        successful=True,
                        max_consecutive_failures=self.config.max_consecutive_failures,
                    )
                    if not task.output_path:
                        continue

                    start_ts = task.started_at or datetime.now(timezone.utc)
                    end_ts = task.completed_at or start_ts
                    duration = (end_ts - start_ts).total_seconds() or task.duration

                    audio_info = recorder.get_audio_info(task.output_path) or {}
                    actual_duration = audio_info.get("duration")
                    duration_ratio = None
                    if actual_duration and duration:
                        duration_ratio = actual_duration / duration

                    shard_id = shard_repo.insert(
                        {
                            "source_id": task.source_id,
                            "start_ts": start_ts,
                            "end_ts": end_ts,
                            "duration": duration,
                            "path": task.output_path,
                            "file_size_bytes": task.file_size,
                            "bitrate": audio_info.get("bitrate"),
                            "codec": audio_info.get("codec"),
                            "sample_rate": audio_info.get("sample_rate", 22050),
                            "channels": audio_info.get("channels", 1),
                            "actual_duration": actual_duration,
                            "duration_ratio": duration_ratio,
                            "capture_status": "captured",
                        }
                    )

                    if extractor is None:
                        shard_repo.update_status(
                            shard_id,
                            "error",
                            error_message="prefilter_unavailable",
                        )
                        continue

                    prefilter = extractor.process_shard(task.output_path)
                    speech_ratio = prefilter.get("speech_ratio")
                    silence_ratio = None
                    if speech_ratio is not None:
                        silence_ratio = max(0.0, min(1.0, 1.0 - speech_ratio))
                    shard_repo.update_status(
                        shard_id,
                        "prefiltered",
                        speech_ratio=speech_ratio,
                        silence_ratio=silence_ratio,
                        total_segments=prefilter.get("total_segments"),
                        speech_segments=prefilter.get("speech_segments"),
                    )

                    station = sources_by_id.get(task.source_id, {})
                    tzinfo, tz_label = _resolve_listening_timezone(
                        station.get("timezone"),
                        self.config.listening_timezone_strategy,
                        self.config.listening_timezone,
                    )
                    local_start = start_ts.astimezone(tzinfo)
                    daypart_repo.upsert(
                        {
                            "source_id": task.source_id,
                            "day": local_start.date(),
                            "daypart": _daypart_from_hour(local_start.hour),
                            "timezone_used": tz_label,
                            "total_seconds": duration,
                            "speech_seconds": duration * (prefilter.get("speech_ratio") or 0.0),
                            "shard_count": 1,
                        }
                    )

                    if audio_lid is None:
                        shard_repo.update_status(
                            shard_id,
                            "error",
                            error_message="audio_lid_unavailable",
                        )
                        continue

                    segments_for_aggregate = []

                    for segment in prefilter.get("segments", []):
                        predictions = audio_lid.predict_segment(
                            task.output_path,
                            segment["start"],
                            segment["end"],
                            top_k=3,
                        )
                        fused_probs = fusion.fuse_predictions(
                            audio_predictions=predictions,
                            min_confidence=0.0,
                        )
                        primary_lang, confidence = fusion.get_primary_language(fused_probs)

                        canonical_probs: Dict[str, float] = {}
                        for lang, prob in fused_probs.items():
                            canonical = label_map.get(lang)
                            if canonical:
                                canonical_probs[canonical] = (
                                    canonical_probs.get(canonical, 0.0) + prob
                                )

                        llm_language = None
                        llm_confidence = None
                        llm_dialect = None
                        llm_rationale = None
                        if llm_classifier:
                            station = sources_by_id.get(task.source_id, {})
                            taxonomy = _fetch_taxonomy(conn, station.get("country"))
                            try:
                                payload = llm_classifier.classify(
                                    taxonomy=taxonomy,
                                    audio_lid_topk=fused_probs,
                                    transcript=None,
                                    station_metadata={
                                        "name": station.get("name"),
                                        "country": station.get("country"),
                                        "tags": station.get("tags", []),
                                        "lang_hint": station.get("lang_hint"),
                                    },
                                )
                                llm_language = payload.get("primary_language")
                                llm_dialect = payload.get("dialect")
                                llm_confidence = payload.get("confidence")
                                llm_rationale = payload.get("rationale")
                                if payload.get("uncertainty_flags"):
                                    pipeline_repo.insert(
                                        stage="lid",
                                        event_type="llm_classifier_warning",
                                        status="warn",
                                        source_id=task.source_id,
                                        shard_id=shard_id,
                                        message="LLM classifier returned non-strict output",
                                        payload={
                                            "uncertainty_flags": payload.get("uncertainty_flags"),
                                            "primary_language": llm_language,
                                        },
                                    )
                            except Exception as e:
                                logger.warning("LLM classification failed", error=str(e))
                                pipeline_repo.insert(
                                    stage="lid",
                                    event_type="llm_classifier_error",
                                    status="error",
                                    source_id=task.source_id,
                                    shard_id=shard_id,
                                    message="LLM classifier failed",
                                    payload={"error": str(e)},
                                )

                        canonical_lang = None
                        if llm_language and llm_language != "unknown":
                            canonical_lang = llm_language
                        elif primary_lang:
                            canonical_lang = label_map_repo.get_canonical(primary_lang)

                        primary_lang_value = canonical_lang or None
                        segment_data = {
                            "shard_id": shard_id,
                            "start": segment["start"],
                            "end": segment["end"],
                            "duration": segment["end"] - segment["start"],
                            "is_speech": segment.get("is_speech", True),
                            "music_prob": segment.get("music_prob"),
                            "lang_probs": fused_probs,
                            "primary_lang": primary_lang_value,
                            "primary_lang_raw": primary_lang,
                            "primary_lang_iso639_3": canonical_lang,
                            "confidence": confidence,
                            "llm_verified_lang": llm_language,
                            "llm_verification_confidence": llm_confidence,
                        }
                        segment_id = segment_repo.insert(segment_data)
                        if llm_language:
                            verification_repo.insert(
                                segment_type="radio",
                                segment_id=segment_id,
                                source="llm",
                                provider="openai",
                                model=llm_classifier.model if llm_classifier else None,
                                candidates=list(fused_probs.keys()),
                                language=llm_language,
                                dialect=llm_dialect,
                                confidence=llm_confidence,
                                rationale=llm_rationale,
                            )
                        segments_for_aggregate.append(segment_data)

                        if canonical_probs:
                            segments_for_aggregate[-1] = {
                                **segment_data,
                                "lang_probs": canonical_probs,
                                "primary_lang": canonical_lang,
                            }

                    shard_repo.update_status(shard_id, "lid_done")

                    hourly = aggregator.aggregate_hourly(
                        segments_for_aggregate,
                        hour=start_ts,
                    )
                    if hourly.get("primary_lang") and len(hourly["primary_lang"]) > 10:
                        hourly["primary_lang"] = None
                    hourly["source_id"] = task.source_id
                    hourly_repo.upsert(hourly)

        except Exception as e:
            logger.error("Capture cycle failed", error=str(e))

    async def start(self):
        """Start the service"""
        if self.running:
            logger.warning("Service already running")
            return

        logger.info("Starting radio ingestion service")

        try:
            # Initialize components
            self.task_queue = TaskQueue(max_size=1000)

            self.processor = PipelineProcessor(
                task_queue=self.task_queue,
                # Callbacks will be set up based on needs
            )

            self.scheduler = TaskScheduler()

            self.backpressure = BackpressureController(
                min_capture_duration=60, max_capture_duration=self.config.capture_duration
            )

            # Register scheduled tasks
            # Daily station refresh
            self.scheduler.register_daily_task(
                name="station_refresh", callback=self.refresh_stations, hour=2, minute=0  # 2 AM UTC
            )

            # Hourly captures
            self.scheduler.register_task(
                name="capture_cycle",
                interval_seconds=self.config.capture_interval_minutes * 60,
                callback=self.capture_stations,
            )

            # Start components
            await self.processor.start(num_workers=2)
            await self.scheduler.start()

            self.running = True

            logger.info("Radio ingestion service started")

            # Main service loop
            while self.running:
                await asyncio.sleep(10.0)  # Check status periodically

        except Exception as e:
            logger.error("Service startup failed", error=str(e))
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the service"""
        if not self.running:
            return

        logger.info("Stopping radio ingestion service")

        self.running = False

        # Stop components
        if self.processor:
            await self.processor.stop()

        if self.scheduler:
            await self.scheduler.stop()

        logger.info("Radio ingestion service stopped")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Dictionary with health status
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
        }

        # Check database
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            health["components"]["database"] = "healthy"
        except Exception as e:
            health["status"] = "degraded"
            health["components"]["database"] = f"unhealthy: {str(e)}"

        # Check queue
        if self.task_queue:
            stats = self.task_queue.get_queue_stats()
            health["components"]["task_queue"] = {"status": "healthy", "stats": stats}
        else:
            health["status"] = "degraded"
            health["components"]["task_queue"] = "not_initialized"

        # Check scheduler
        if self.scheduler:
            scheduler_stats = self.scheduler.get_stats()
            health["components"]["scheduler"] = {"status": "healthy", "stats": scheduler_stats}
        else:
            health["status"] = "degraded"
            health["components"]["scheduler"] = "not_initialized"

        # Check backpressure
        if self.backpressure:
            health["components"]["backpressure"] = {
                "status": "healthy",
                "status_details": self.backpressure.get_status(),
            }

        return health


async def main():
    """Main entry point"""
    config = get_config()

    service = RadioIngestionService(config)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
