"""Metadata harvester module for SVI data collection.

This module provides the MetaHarvester class for systematic metadata
collection from Google Street View and Baidu Street View platforms.

The implementation extends the spider-web sampling method described in
Wang et al. (2025) with improved spatial coverage and data validation.

References:
    Wang, L., et al. (2025). The optimal sampling interval of street view
    images for urban analytics. Transportation Research Part D (TUSDT).
"""

import os
import time
import json
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlencode

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point
from tqdm import tqdm

from urban_svi_qa.config import PLATFORM_CONFIG, get_platform_params
from urban_svi_qa.utils.geometry import transform_wgs84_to_bd09, calculate_haversine_distance


@dataclass
class SVIMetadata:
    """Data class for Street View Image metadata.
    
    Attributes:
        pano_id: Unique panorama identifier.
        lat: Latitude of the panorama (WGS84).
        lng: Longitude of the panorama (WGS84).
        date: Capture date (YYYYMMDD format).
        north_angle: Compass heading of the panorama (degrees).
        tilt: Tilt angle (degrees).
        roll: Roll angle (degrees).
        pano_yaw: Panorama yaw angle (degrees).
        tilt_yaw: Tilt yaw angle (degrees).
        roll_pitch: Roll pitch angle (degrees).
        image_width: Image width in pixels.
        image_height: Image height in pixels.
        tile_width: Tile width in pixels (if tiled).
        tile_height: Tile height in pixels (if tiled).
        num_tiles_x: Number of horizontal tiles.
        num_tiles_y: Number of vertical tiles.
        source: Platform source ('google' or 'baidu').
        raw_response: Raw API response (optional).
    """
    pano_id: str
    lat: float
    lng: float
    date: Optional[int] = None
    north_angle: Optional[float] = None
    tilt: Optional[float] = None
    roll: Optional[float] = None
    pano_yaw: Optional[float] = None
    tilt_yaw: Optional[float] = None
    roll_pitch: Optional[float] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    tile_width: Optional[int] = None
    tile_height: Optional[int] = None
    num_tiles_x: Optional[int] = None
    num_tiles_y: Optional[int] = None
    source: str = "unknown"
    raw_response: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_series(self) -> pd.Series:
        """Convert to pandas Series."""
        return pd.Series(self.to_dict())


class BaseHarvester(ABC):
    """Abstract base class for SVI metadata harvesters.
    
    This class defines the interface that all platform-specific harvesters
    must implement. It follows the Strategy pattern to allow platform-agnostic
    usage while maintaining platform-specific implementations.
    
    Attributes:
        platform: Name of the SVI platform ('google' or 'baidu').
        api_key: API key for the platform (read from environment variable).
        timeout: Request timeout in seconds.
    """

    def __init__(self, platform: str, api_key: Optional[str] = None) -> None:
        """Initialize the base harvester.
        
        Args:
            platform: SVI platform name ('google' or 'baidu').
            api_key: Optional API key. If not provided, reads from environment.
            
        Raises:
            ValueError: If platform is not supported.
            RuntimeError: If API key is not provided and not found in environment.
        """
        self.platform = platform.lower()
        self.config = PLATFORM_CONFIG.get(self.platform, {})
        
        # Get API key from parameter or environment
        if api_key:
            self.api_key = api_key
        else:
            env_var = f"{self.platform.upper()}_API_KEY"
            self.api_key = os.environ.get(env_var)
            
        if not self.api_key:
            raise RuntimeError(
                f"API key required. Provide api_key parameter or set {env_var} "
                "environment variable."
            )
            
        self.timeout = self.config.get("request_timeout", 30)
        self._session = requests.Session()
        self._request_count = 0
        self._last_request_time = 0.0

    @abstractmethod
    def fetch_metadata(self, lat: float, lng: float) -> Optional[SVIMetadata]:
        """Fetch metadata for a single coordinate.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            SVIMetadata object or None if no SVI available.
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate API connectivity and credentials.
        
        Returns:
            True if connection is valid, False otherwise.
        """
        pass

    def _rate_limit(self, min_interval: float = 0.05) -> None:
        """Implement rate limiting to respect API quotas.
        
        Args:
            min_interval: Minimum time between requests in seconds.
        """
        self._request_count += 1
        
        # Calculate time since last request
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        # Wait if needed
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self._last_request_time = time.time()
        
        # Platform-specific rate limiting
        if self.platform == "google" and self._request_count % 50 == 0:
            time.sleep(1)  # Brief pause every 50 requests

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        retries: int = 3,
    ) -> Optional[Dict]:
        """Make HTTP request with retry logic.
        
        Args:
            url: Request URL.
            params: Query parameters.
            retries: Number of retry attempts.
            
        Returns:
            JSON response as dictionary, or None if failed.
        """
        self._rate_limit()
        
        for attempt in range(retries):
            try:
                response = self._session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                
                # Try to parse JSON
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"text": response.text, "status_code": response.status_code}
                    
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    print(f"Request failed after {retries} attempts: {e}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None


class MetaHarvester(BaseHarvester):
    """Metadata harvester for SVI platforms.
    
    This class implements the spider-web sampling strategy for systematic
    metadata collection. It extends the original Wang et al. (2025) method
    by adding intelligent boundary detection and duplicate prevention.
    
    Attributes:
        platform: Name of the SVI platform.
        collected_ids: Set of already collected panorama IDs.
        
    Example:
        >>> harvester = MetaHarvester(platform='google')
        >>> metadata = harvester.fetch_metadata(22.2839, 114.1574)
        >>> print(metadata.pano_id)
    """

    def __init__(
        self,
        platform: str,
        api_key: Optional[str] = None,
        boundary_gdf: Optional[gpd.GeoDataFrame] = None,
        database_path: Optional[str] = None,
    ) -> None:
        """Initialize the metadata harvester.
        
        Args:
            platform: SVI platform ('google' or 'baidu').
            api_key: Optional API key.
            boundary_gdf: Optional GeoDataFrame defining study area boundary.
            database_path: Optional path to SQLite database for persistence.
            
        Note:
            If boundary_gdf is provided, all coordinates will be validated
            against this boundary before API calls.
        """
        super().__init__(platform, api_key)
        self.boundary_gdf = boundary_gdf
        self.collected_ids: Set[str] = set()
        self._temp_queue: List[str] = []  # For spider-web traversal
        
        # Load platform parameters
        self.params = get_platform_params(platform)
        
        # Initialize database if provided
        self.database_path = database_path
        if database_path:
            self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database for metadata storage."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                pano_id TEXT PRIMARY KEY,
                lat REAL,
                lng REAL,
                date INTEGER,
                north_angle REAL,
                tilt REAL,
                roll REAL,
                image_width INTEGER,
                image_height INTEGER,
                source TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create queue table for spider-web traversal
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                pano_id TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

    def validate_connection(self) -> bool:
        """Validate API connectivity with a test request.
        
        Returns:
            True if API is accessible and credentials are valid.
            
        Note:
            Uses a known valid coordinate (Hong Kong Central) for testing.
        """
        try:
            # Test with Hong Kong Central coordinates
            test_result = self.fetch_metadata(22.2839, 114.1574)
            return test_result is not None
        except Exception as e:
            print(f"Connection validation failed: {e}")
            return False

    def fetch_metadata(self, lat: float, lng: float) -> Optional[SVIMetadata]:
        """Fetch metadata for a single coordinate.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            SVIMetadata object or None if no SVI available.
            
        Raises:
            ValueError: If coordinates are outside the study boundary.
            
        Note:
            Logic derived from Wang et al. (2025, TUSDT) Section 3.1.
        """
        # Check boundary if provided
        if self.boundary_gdf is not None:
            if not self._is_within_boundary(lat, lng):
                raise ValueError(f"Coordinates ({lat}, {lng}) outside study boundary")

        # Platform-specific implementation
        if self.platform == "google":
            return self._fetch_google_metadata(lat, lng)
        elif self.platform == "baidu":
            return self._fetch_baidu_metadata(lat, lng)
        else:
            raise NotImplementedError(f"Platform {self.platform} not implemented")

    def _is_within_boundary(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within study boundary.
        
        Args:
            lat: Latitude.
            lng: Longitude.
            
        Returns:
            True if point is within or touches boundary.
        """
        if self.boundary_gdf is None:
            return True
        point = Point(lng, lat)
        return self.boundary_gdf.geometry.contains(point).any()

    def _fetch_google_metadata(self, lat: float, lng: float) -> Optional[SVIMetadata]:
        """Fetch metadata from Google Street View Static API.
        
        Args:
            lat: Latitude in WGS84.
            lng: Longitude in WGS84.
            
        Returns:
            SVIMetadata object or None if no SVI available.
            
        Note:
            Uses the Street View Static API metadata endpoint.
            See: https://developers.google.com/maps/documentation/streetview/metadata
        """
        base_url = self.config.get("metadata_url", 
                                   "https://maps.googleapis.com/maps/api/streetview/metadata")
        
        params = {
            "location": f"{lat},{lng}",
            "key": self.api_key,
        }
        
        data = self._make_request(base_url, params)
        
        if data is None:
            return None
        
        # Check status
        status = data.get("status")
        if status != "OK":
            return None
        
        # Parse location
        location = data.get("location", {})
        
        # Parse date (format: YYYY-MM)
        date_str = data.get("date")
        date_int = None
        if date_str:
            try:
                year, month = date_str.split("-")
                date_int = int(year) * 10000 + int(month) * 100 + 1
            except ValueError:
                pass
        
        metadata = SVIMetadata(
            pano_id=data.get("pano_id", ""),
            lat=location.get("lat", lat),
            lng=location.get("lng", lng),
            date=date_int,
            north_angle=data.get("north_angle"),
            image_width=640,  # Default GSV resolution
            image_height=480,
            source="google",
            raw_response=data,
        )
        
        return metadata

    def _fetch_baidu_metadata(self, lat: float, lng: float) -> Optional[SVIMetadata]:
        """Fetch metadata from Baidu Street View API.
        
        Args:
            lat: Latitude in WGS84 (will be converted to BD09).
            lng: Longitude in WGS84 (will be converted to BD09).
            
        Returns:
            SVIMetadata object or None.
            
        Note:
            Baidu API requires BD09 coordinates and different parameters.
        """
        # Convert WGS84 to BD09
        bd_lng, bd_lat = transform_wgs84_to_bd09(lng, lat)
        
        # Baidu API endpoint for panorama info
        # Note: This is a simplified implementation. Actual Baidu API
        # requires proper authentication and may have different endpoints.
        base_url = "https://map.baidu.com"
        
        params = {
            "qt": "panoinfo",
            "x": bd_lng,
            "y": bd_lat,
            "ak": self.api_key,
        }
        
        data = self._make_request(base_url, params)
        
        if data is None:
            return None
        
        # Parse Baidu response (structure may vary)
        if data.get("result") != "0" and data.get("result") != 0:
            return None
        
        content = data.get("content", {})
        
        # Parse date (format may vary in Baidu API)
        date_int = None
        date_str = content.get("Date")
        if date_str:
            try:
                date_int = int(date_str)
            except ValueError:
                pass
        
        metadata = SVIMetadata(
            pano_id=str(content.get("ID", "")),
            lat=lat,  # Return original WGS84 coordinates
            lng=lng,
            date=date_int,
            north_angle=content.get("MoveDir"),
            image_width=1024,  # BSV panoramic default
            image_height=512,
            source="baidu",
            raw_response=data,
        )
        
        return metadata

    def fetch_adjacent_panoramas(
        self,
        pano_id: str,
        lat: float,
        lng: float,
    ) -> List[Tuple[str, float, float]]:
        """Fetch adjacent panorama IDs from a given panorama.
        
        This is the core of the spider-web sampling method from Wang et al. (2025).
        It finds neighboring panoramas by querying in cardinal directions.
        
        Args:
            pano_id: Current panorama ID.
            lat: Current latitude.
            lng: Current longitude.
            
        Returns:
            List of tuples (adjacent_pano_id, lat, lng).
            
        Note:
            The spider-web method samples in a breadth-first manner,
            exploring all adjacent panoramas before moving further.
        """
        adjacent = []
        
        # Query points in 4 cardinal directions at optimal interval
        interval = self.params["optimal_interval"]
        
        # Approximate degree offsets (rough approximation)
        lat_offset = interval / 111000  # ~1 degree = 111 km
        lng_offset = interval / (111000 * np.cos(np.radians(lat)))
        
        directions = [
            (lat + lat_offset, lng),  # North
            (lat - lat_offset, lng),  # South
            (lat, lng + lng_offset),  # East
            (lat, lng - lng_offset),  # West
        ]
        
        for new_lat, new_lng in directions:
            # Check boundary
            if not self._is_within_boundary(new_lat, new_lng):
                continue
            
            # Fetch metadata at this location
            metadata = self.fetch_metadata(new_lat, new_lng)
            
            if metadata and metadata.pano_id and metadata.pano_id != pano_id:
                # Check if already collected
                if metadata.pano_id not in self.collected_ids:
                    adjacent.append((metadata.pano_id, metadata.lat, metadata.lng))
        
        return adjacent

    def collect_from_seed(
        self,
        seed_lat: float,
        seed_lng: float,
        max_samples: int = 1000,
        max_iterations: int = 100,
        save_interval: int = 100,
        progress_bar: bool = True,
    ) -> pd.DataFrame:
        """Collect metadata using spider-web sampling from a seed point.
        
        This method implements the extended spider-web sampling algorithm
        described in Wang et al. (2025), which traverses the street network
        by following adjacent panoramas from an initial seed point.
        
        Args:
            seed_lat: Seed point latitude.
            seed_lng: Seed point longitude.
            max_samples: Maximum number of samples to collect.
            max_iterations: Safety limit for iteration count.
            save_interval: Save progress to database every N samples.
            progress_bar: Whether to show progress bar.
            
        Returns:
            DataFrame containing collected metadata.
            
        Note:
            This is the core sampling method based on Wang et al. (2025).
            It systematically explores the street network while avoiding
            duplicates and respecting API rate limits.
        """
        # Initialize queue with seed
        queue: List[Tuple[str, float, float]] = []
        results: List[Dict] = []
        
        # Fetch seed metadata
        seed_metadata = self.fetch_metadata(seed_lat, seed_lng)
        if seed_metadata is None:
            print("Warning: No SVI at seed location")
            return pd.DataFrame()
        
        self.collected_ids.add(seed_metadata.pano_id)
        results.append(seed_metadata.to_dict())
        
        # Add seed's neighbors to queue
        neighbors = self.fetch_adjacent_panoramas(
            seed_metadata.pano_id,
            seed_metadata.lat,
            seed_metadata.lng,
        )
        queue.extend(neighbors)
        
        # Spider-web traversal
        iterations = 0
        pbar = tqdm(total=max_samples, disable=not progress_bar, desc="Collecting SVI")
        pbar.update(1)
        
        while queue and len(results) < max_samples and iterations < max_iterations:
            iterations += 1
            
            # Get next item from queue
            pano_id, lat, lng = queue.pop(0)
            
            # Skip if already collected
            if pano_id in self.collected_ids:
                continue
            
            # Fetch full metadata
            try:
                metadata = self.fetch_metadata(lat, lng)
                if metadata is None:
                    continue
            except ValueError:
                # Outside boundary
                continue
            
            # Add to results
            self.collected_ids.add(metadata.pano_id)
            results.append(metadata.to_dict())
            pbar.update(1)
            
            # Save to database periodically
            if self.database_path and len(results) % save_interval == 0:
                self._save_to_database(results[-save_interval:])
            
            # Find neighbors and add to queue
            new_neighbors = self.fetch_adjacent_panoramas(
                metadata.pano_id,
                metadata.lat,
                metadata.lng,
            )
            
            for neighbor in new_neighbors:
                if neighbor[0] not in self.collected_ids:
                    queue.append(neighbor)
            
            # Rate limiting
            time.sleep(0.1)
        
        pbar.close()
        
        # Final save
        if self.database_path and results:
            self._save_to_database(results)
        
        return pd.DataFrame(results)

    def _save_to_database(self, records: List[Dict]) -> None:
        """Save records to SQLite database.
        
        Args:
            records: List of metadata dictionaries.
        """
        if not self.database_path:
            return
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        for record in records:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO metadata 
                    (pano_id, lat, lng, date, north_angle, tilt, roll,
                     image_width, image_height, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.get('pano_id'),
                    record.get('lat'),
                    record.get('lng'),
                    record.get('date'),
                    record.get('north_angle'),
                    record.get('tilt'),
                    record.get('roll'),
                    record.get('image_width'),
                    record.get('image_height'),
                    record.get('source'),
                ))
            except sqlite3.Error as e:
                print(f"Database error: {e}")
        
        conn.commit()
        conn.close()

    def collect_from_points(
        self,
        points: List[Tuple[float, float]],
        progress_bar: bool = True,
    ) -> pd.DataFrame:
        """Collect metadata from a list of specific coordinates.
        
        Args:
            points: List of (lat, lng) tuples.
            progress_bar: Whether to show progress bar.
            
        Returns:
            DataFrame containing collected metadata.
        """
        results = []
        
        for lat, lng in tqdm(points, disable=not progress_bar, desc="Collecting"):
            try:
                metadata = self.fetch_metadata(lat, lng)
                if metadata:
                    results.append(metadata.to_dict())
            except ValueError:
                # Outside boundary
                continue
            except Exception as e:
                print(f"Error at ({lat}, {lng}): {e}")
                continue
            
            # Rate limiting
            time.sleep(0.05)
        
        return pd.DataFrame(results)

    def load_from_database(self) -> pd.DataFrame:
        """Load previously collected metadata from database.
        
        Returns:
            DataFrame containing all metadata from database.
        """
        if not self.database_path:
            return pd.DataFrame()
        
        conn = sqlite3.connect(self.database_path)
        df = pd.read_sql_query("SELECT * FROM metadata", conn)
        conn.close()
        
        # Update collected_ids
        self.collected_ids = set(df['pano_id'].tolist())
        
        return df
