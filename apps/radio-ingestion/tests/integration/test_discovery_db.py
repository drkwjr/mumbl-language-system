"""Integration tests for discovery module with database"""

from datetime import datetime, timezone

import pytest
from mumbl_storage.db import DatabaseConfig, get_connection
from radio_ingestion.discovery.radio_browser import discover_stations
from radio_ingestion.storage.radio_repositories import RadioSourceRepository


@pytest.mark.integration
def test_discover_and_store_stations():
    """Test discovering stations and storing in database"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    # Discover stations (use Somalia as test case)
    stations = discover_stations(
        api_url="https://de1.api.radio-browser.info/json",
        country="SOM",  # Somalia ISO code
        limit=5,
    )

    if len(stations) == 0:
        pytest.skip("No stations returned from Radio Browser API")

    # Store in database
    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)
        source_ids = source_repo.insert_many(stations)

        # Verify inserts
        assert len(source_ids) > 0, "Should have inserted at least one source"
        assert any(
            sid is not None for sid in source_ids
        ), "Should have at least one successful insert"

        # Verify data integrity
        for source_id, station in zip(source_ids, stations):
            if source_id is not None:
                stored = source_repo.get_by_id(source_id)
                assert stored is not None, f"Source {source_id} should exist"
                assert stored["name"] == station["name"], "Name should match"
                assert stored["stream_url"] == station["stream_url"], "Stream URL should match"


@pytest.mark.integration
def test_list_active_sources():
    """Test listing active sources from database"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)

        # List all active sources
        all_sources = source_repo.list_active()
        assert isinstance(all_sources, list), "Should return a list"

        # Filter by country (may be empty if no sources from Somalia)
        som_sources = source_repo.list_active(country="SOM")
        assert isinstance(som_sources, list), "Should return a list"

        # If sources exist, verify they're from Somalia
        if som_sources:
            for source in som_sources:
                country = source.get("country", "").upper()
                assert (
                    country == "SOM"
                ), f"Source {source.get('id')} should be from Somalia, got {country}"


@pytest.mark.integration
def test_duplicate_prevention():
    """Test that duplicate stations are not inserted"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    # Discover a small set of stations
    stations = discover_stations(
        api_url="https://de1.api.radio-browser.info/json", country="SOM", limit=3
    )

    if len(stations) == 0:
        pytest.skip("No stations found to test with")

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)

        # Insert first time
        first_ids = source_repo.insert_many(stations)
        first_count = len([sid for sid in first_ids if sid is not None])

        # Insert again (should be updates, not new inserts)
        second_ids = source_repo.insert_many(stations)

        # Should return same IDs (or updates)
        assert len(second_ids) == len(first_ids), "Should return same number of IDs"

        # Verify data is updated
        for source_id in first_ids:
            if source_id is not None:
                source = source_repo.get_by_id(source_id)
                assert source is not None, f"Source {source_id} should still exist"
                assert source["last_check"] is not None, "last_check should be updated"


@pytest.mark.integration
def test_update_last_check():
    """Test updating last check timestamp and health metadata"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)

        # Get first active source (no limit parameter, just take first)
        sources = source_repo.list_active()
        if not sources:
            pytest.skip("No active sources to test with")

        source = sources[0]
        source_id = source["id"]

        # Update last check + health
        source_repo.update_health(source_id, successful=True, max_consecutive_failures=3)

        # Verify update
        updated = source_repo.get_by_id(source_id)
        assert updated["last_check"] is not None, "last_check should be set"
        assert (
            updated["last_successful_capture"] is not None
        ), "last_successful_capture should be set"
        assert updated["health_status"] == "healthy", "health_status should be healthy"
        assert updated["health_consecutive_failures"] == 0, "failures should reset on success"
