-- Migration 006: Product-layer views for radio pipeline
-- Created: 2025-12-27
-- Purpose: Provide coherent, query-friendly views over radio segments and scores

DO $$
BEGIN
    IF to_regclass('public.radio_segments') IS NOT NULL THEN
        EXECUTE $view$
            CREATE OR REPLACE VIEW radio_segment_product_view AS
            SELECT
                seg.id AS radio_segment_id,
                seg.shard_id AS shard_id,
                shard.source_id AS source_id,
                src.name AS station_name,
                src.country AS station_country,
                shard.path AS audio_path,
                shard.start_ts AS shard_start_ts,
                shard.end_ts AS shard_end_ts,
                seg.start_sec AS start_time,
                seg.end_sec AS end_time,
                seg.duration AS duration,
                seg.is_speech AS is_speech,
                seg.music_prob AS music_prob,
                seg.primary_lang AS lang,
                seg.confidence AS lid_confidence,
                seg.lang_probs AS lang_probs,
                seg.text_lang AS text_lang,
                seg.text_confidence AS text_confidence,
                seg.llm_verified_lang AS llm_verified_lang,
                seg.llm_verification_confidence AS llm_verification_confidence,
                seg.created_at AS segment_created_at,
                shard.created_at AS shard_created_at
            FROM radio_segments seg
            JOIN radio_shards shard ON shard.id = seg.shard_id
            JOIN radio_sources src ON src.id = shard.source_id
        $view$;
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.segment_scores') IS NOT NULL THEN
        EXECUTE $view$
            CREATE OR REPLACE VIEW radio_segment_scores_view AS
            SELECT
                scores.id AS score_id,
                scores.segment_type AS segment_type,
                scores.segment_id AS segment_id,
                scores.clarity AS clarity,
                scores.alignment AS alignment,
                scores.diarization AS diarization,
                scores.transcript_accuracy AS transcript_accuracy,
                scores.validity AS validity,
                scores.shape AS shape,
                scores.total AS total,
                scores.eligible_learner AS eligible_learner,
                scores.eligible_training AS eligible_training,
                scores.policy_flags AS policy_flags,
                scores.notes AS notes,
                scores.created_at AS created_at,
                seg.shard_id AS shard_id,
                shard.source_id AS source_id,
                src.name AS station_name,
                seg.primary_lang AS primary_lang,
                seg.confidence AS lid_confidence
            FROM segment_scores scores
            JOIN radio_segments seg
                ON scores.segment_type = 'radio'
                AND scores.segment_id = seg.id
            JOIN radio_shards shard ON shard.id = seg.shard_id
            JOIN radio_sources src ON src.id = shard.source_id
        $view$;
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.radio_segment_product_view') IS NOT NULL THEN
        EXECUTE $view$
            COMMENT ON VIEW radio_segment_product_view
            IS 'Product-layer view over radio segments with station/shard context'
        $view$;
    END IF;

    IF to_regclass('public.radio_segment_scores_view') IS NOT NULL THEN
        EXECUTE $view$
            COMMENT ON VIEW radio_segment_scores_view
            IS 'Product-layer view for radio segment scores with station context'
        $view$;
    END IF;
END $$;
