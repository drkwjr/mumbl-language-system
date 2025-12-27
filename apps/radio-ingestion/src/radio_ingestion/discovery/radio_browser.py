"""Radio Browser API integration for station discovery"""

import time
import requests
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class RadioBrowserClient:
    """Client for Radio Browser API"""
    
    def __init__(
        self,
        api_url: str = "https://de1.api.radio-browser.info/json",
        timeout_seconds: int = 30,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.5,
    ):
        """
        Initialize Radio Browser client.
        
        Args:
            api_url: Radio Browser API endpoint
        """
        self.api_url = api_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.session = requests.Session()
        # Set user agent as recommended by Radio Browser API
        self.session.headers.update({
            'User-Agent': 'MumblLanguageSystem/0.1.0 (educational/research)'
        })
    
    def search_stations(
        self,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
        language: Optional[str] = None,
        tag: Optional[str] = None,
        tag_exact: bool = False,
        limit: int = 100,
        offset: int = 0,
        order: str = "votes",
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for radio stations.
        
        Args:
            country: ISO 3166-1 alpha-3 country code (e.g., 'SOM' for Somalia)
            language: Language code (e.g., 'somali')
            tag: Tag to filter by (e.g., 'news', 'talk')
            tag_exact: Whether tag must match exactly
            limit: Maximum number of results
            offset: Offset for pagination
            order: Field to order by ('name', 'country', 'votes', 'clickcount', etc.)
            reverse: Whether to reverse sort order
            
        Returns:
            List of station dictionaries
        """
        params = {
            'limit': limit,
            'offset': offset,
            'order': order,
            'reverse': str(reverse).lower()
        }
        
        if country_code:
            params['countrycode'] = country_code
        elif country:
            params['country'] = country
        if language:
            params['language'] = language
        if tag:
            params['tag'] = tag
            params['tag_exact'] = str(tag_exact).lower()
        
        url = f"{self.api_url}/stations/search"
        
        try:
            logger.info(
                "Searching Radio Browser API",
                url=url,
                params=params
            )
            
            attempt = 0
            while True:
                try:
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                    response.raise_for_status()

                    stations = response.json()

                    logger.info(
                        "Radio Browser API search successful",
                        stations_found=len(stations)
                    )

                    return stations
                except requests.exceptions.RequestException as e:
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    logger.warning(
                        "Radio Browser API request failed, retrying",
                        error=str(e),
                        attempt=attempt,
                        max_retries=self.max_retries,
                        url=url,
                    )
                    time.sleep(self.retry_backoff_seconds * attempt)
            
        except requests.exceptions.RequestException as e:
            logger.error(
                "Radio Browser API request failed",
                error=str(e),
                url=url,
                params=params
            )
            raise
    
    def get_station_by_uuid(self, station_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get station details by UUID.
        
        Args:
            station_uuid: Station UUID from Radio Browser
        
        Returns:
            Station dictionary or None if not found
        """
        url = f"{self.api_url}/stations/byuuid/{station_uuid}"
        
        try:
            response = self.session.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            stations = response.json()
            
            if stations:
                return stations[0]
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to get station by UUID",
                station_uuid=station_uuid,
                error=str(e)
            )
            return None
    
    def parse_station(self, station_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize station data from Radio Browser API.
        
        Args:
            station_data: Raw station data from API
        
        Returns:
            Normalized station dictionary
        """
        # Extract stream URL (prefer https, fallback to http)
        stream_urls = []
        for url_field in ['url_resolved', 'url', 'url_secure']:
            if station_data.get(url_field):
                stream_urls.append(station_data[url_field])
        
        stream_url = stream_urls[0] if stream_urls else None
        
        # Parse tags
        tags = []
        if station_data.get('tags'):
            tags = [tag.strip() for tag in station_data['tags'].split(',') if tag.strip()]
        
        lang_hint = station_data.get('language', '').strip()
        if lang_hint:
            lang_hint = lang_hint.split(',')[0].strip().lower()
            if len(lang_hint) > 50:
                lang_hint = lang_hint[:50]
        else:
            lang_hint = None

        return {
            'name': station_data.get('name', 'Unknown'),
            'stream_url': stream_url,
            'country': station_data.get('countrycode', '').upper() if station_data.get('countrycode') else None,
            'timezone': station_data.get('timezone'),
            'lang_hint': lang_hint,
            'bitrate': station_data.get('bitrate'),
            'codec': station_data.get('codec'),
            'station_uuid': station_data.get('stationuuid'),
            'homepage': station_data.get('homepage'),
            'tags': tags,
            'votes': station_data.get('votes', 0),
            'clickcount': station_data.get('clickcount', 0),
        }


def discover_stations(
    api_url: str,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 10,
    timeout_seconds: int = 30,
    max_retries: int = 2,
) -> List[Dict[str, Any]]:
    """
    Discover radio stations from Radio Browser API.
    
    Args:
        api_url: Radio Browser API endpoint
        country: ISO 3166-1 alpha-3 country code (e.g., 'SOM')
        language: Language filter (optional)
        limit: Maximum number of stations to return
    
    Returns:
        List of normalized station dictionaries
    """
    client = RadioBrowserClient(
        api_url=api_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    
    # Search stations
    stations = client.search_stations(
        country=country,
        country_code=country_code,
        language=language,
        limit=limit,
        order='votes',
        reverse=True
    )
    
    # Parse and normalize
    parsed_stations = []
    for station in stations:
        try:
            parsed = client.parse_station(station)
            if parsed['stream_url']:  # Only include stations with valid stream URLs
                parsed_stations.append(parsed)
        except Exception as e:
            logger.warning(
                "Failed to parse station",
                station_name=station.get('name'),
                error=str(e)
            )
            continue
    
    logger.info(
        "Station discovery complete",
        total_found=len(stations),
        valid_stations=len(parsed_stations),
        country=country,
        language=language
    )
    
    return parsed_stations


if __name__ == "__main__":
    """CLI entry point for testing"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Discover radio stations")
    parser.add_argument("--api-url", default="https://de1.api.radio-browser.info/json")
    parser.add_argument("--country", help="Country code (ISO 3166-1 alpha-3)")
    parser.add_argument("--language", help="Language filter")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    
    args = parser.parse_args()
    
    stations = discover_stations(
        api_url=args.api_url,
        country=args.country,
        language=args.language,
        limit=args.limit,
        timeout_seconds=args.timeout,
        max_retries=args.retries,
    )
    
    print(json.dumps(stations, indent=2))
