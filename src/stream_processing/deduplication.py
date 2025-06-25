#!/usr/bin/env python3
"""
Deduplication Engine
Implements locality-sensitive hashing (LSH) for spatial-temporal deduplication
Clusters accidents within 0.1mi radius/2min window
"""

import hashlib
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

import redis
from geopy.distance import geodesic

from ..utils.config import Config
from ..utils.logger import StructuredLogger


@dataclass
class AccidentEvent:
    """Represents an accident event for deduplication"""

    id: str
    source: str
    lat: float
    lon: float
    timestamp: int  # Unix timestamp in milliseconds
    title: str
    description: str
    raw_data: Dict

    def __post_init__(self):
        """Validate accident event data"""
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"Invalid latitude: {self.lat}")
        if not (-180 <= self.lon <= 180):
            raise ValueError(f"Invalid longitude: {self.lon}")
        if self.timestamp <= 0:
            raise ValueError(f"Invalid timestamp: {self.timestamp}")


@dataclass
class AccidentCluster:
    """Represents a cluster of deduplicated accidents"""

    cluster_id: str
    primary_event: AccidentEvent
    duplicate_events: List[AccidentEvent]
    confidence_score: float
    created_at: datetime

    @property
    def total_events(self) -> int:
        return 1 + len(self.duplicate_events)

    @property
    def sources(self) -> Set[str]:
        sources = {self.primary_event.source}
        sources.update(event.source for event in self.duplicate_events)
        return sources


class SpatialTemporalLSH:
    """Locality-Sensitive Hashing for spatial-temporal data"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        # LSH parameters
        self.spatial_precision = 4  # Decimal places for lat/lon
        self.temporal_precision = 60  # Seconds for time buckets
        self.radius_miles = config.deduplication_radius_miles
        self.time_window_minutes = config.deduplication_time_window_minutes

        # Redis for storing hash buckets
        self.redis_client = redis.from_url(config.redis_url)
        self.hash_ttl = config.redis_ttl_seconds

    def _spatial_hash(self, lat: float, lon: float) -> str:
        """Generate spatial hash for given coordinates"""
        # Round coordinates to create spatial buckets
        lat_bucket = round(lat, self.spatial_precision)
        lon_bucket = round(lon, self.spatial_precision)

        # Create hash from spatial coordinates
        spatial_key = f"{lat_bucket:.{self.spatial_precision}f},{lon_bucket:.{self.spatial_precision}f}"
        return hashlib.md5(spatial_key.encode()).hexdigest()[:8]

    def _temporal_hash(self, timestamp: int) -> str:
        """Generate temporal hash for given timestamp"""
        # Convert to seconds and create time buckets
        timestamp_seconds = timestamp // 1000
        time_bucket = (
            timestamp_seconds // self.temporal_precision
        ) * self.temporal_precision

        # Create hash from temporal bucket
        temporal_key = str(time_bucket)
        return hashlib.md5(temporal_key.encode()).hexdigest()[:8]

    def _generate_hash_keys(self, event: AccidentEvent) -> List[str]:
        """Generate multiple hash keys for an event to handle boundary cases"""
        hash_keys = []

        # Generate spatial hashes for nearby grid cells
        lat_offsets = [-0.001, 0, 0.001]  # Small offsets to catch boundary cases
        lon_offsets = [-0.001, 0, 0.001]

        for lat_offset in lat_offsets:
            for lon_offset in lon_offsets:
                spatial_hash = self._spatial_hash(
                    event.lat + lat_offset, event.lon + lon_offset
                )

                # Generate temporal hashes for nearby time buckets
                time_offsets = [-self.temporal_precision, 0, self.temporal_precision]

                for time_offset in time_offsets:
                    temporal_hash = self._temporal_hash(
                        event.timestamp + time_offset * 1000
                    )

                    # Combine spatial and temporal hashes
                    combined_key = f"accident_lsh:{spatial_hash}:{temporal_hash}"
                    hash_keys.append(combined_key)

        return list(set(hash_keys))  # Remove duplicates

    def _calculate_distance(
        self, event1: AccidentEvent, event2: AccidentEvent
    ) -> float:
        """Calculate distance between two events in miles"""
        coord1 = (event1.lat, event1.lon)
        coord2 = (event2.lat, event2.lon)
        return geodesic(coord1, coord2).miles

    def _calculate_time_difference(
        self, event1: AccidentEvent, event2: AccidentEvent
    ) -> float:
        """Calculate time difference between two events in minutes"""
        time_diff_ms = abs(event1.timestamp - event2.timestamp)
        return time_diff_ms / (1000 * 60)  # Convert to minutes

    def _calculate_similarity_score(
        self, event1: AccidentEvent, event2: AccidentEvent
    ) -> float:
        """Calculate similarity score between two events (0-1)"""
        # Spatial similarity
        distance = self._calculate_distance(event1, event2)
        spatial_score = max(0, 1 - (distance / self.radius_miles))

        # Temporal similarity
        time_diff = self._calculate_time_difference(event1, event2)
        temporal_score = max(0, 1 - (time_diff / self.time_window_minutes))

        # Text similarity (simple keyword matching)
        text_score = self._calculate_text_similarity(event1, event2)

        # Combined score (weighted average)
        combined_score = spatial_score * 0.4 + temporal_score * 0.4 + text_score * 0.2

        return combined_score

    def _calculate_text_similarity(
        self, event1: AccidentEvent, event2: AccidentEvent
    ) -> float:
        """Calculate text similarity between event descriptions"""
        # Simple keyword-based similarity
        text1 = (event1.title + " " + event1.description).lower()
        text2 = (event2.title + " " + event2.description).lower()

        # Extract keywords
        keywords1 = set(text1.split())
        keywords2 = set(text2.split())

        if not keywords1 or not keywords2:
            return 0.0

        # Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        return len(intersection) / len(union) if union else 0.0

    def _is_duplicate(self, event1: AccidentEvent, event2: AccidentEvent) -> bool:
        """Determine if two events are duplicates"""
        # Check spatial proximity
        distance = self._calculate_distance(event1, event2)
        if distance > self.radius_miles:
            return False

        # Check temporal proximity
        time_diff = self._calculate_time_difference(event1, event2)
        if time_diff > self.time_window_minutes:
            return False

        # Calculate overall similarity
        similarity = self._calculate_similarity_score(event1, event2)

        # Threshold for considering events as duplicates
        duplicate_threshold = 0.7

        return similarity >= duplicate_threshold

    def add_event(self, event: AccidentEvent) -> Optional[str]:
        """Add event to LSH index and return cluster ID if it's part of a cluster"""
        try:
            hash_keys = self._generate_hash_keys(event)

            # Check for potential duplicates in each hash bucket
            potential_duplicates = []

            for hash_key in hash_keys:
                # Get events from this hash bucket
                bucket_events = self.redis_client.smembers(hash_key)

                for event_data in bucket_events:
                    try:
                        stored_event = self._deserialize_event(event_data.decode())
                        if self._is_duplicate(event, stored_event):
                            potential_duplicates.append(stored_event)
                    except Exception as e:
                        self.logger.warning(f"Failed to deserialize stored event: {e}")

            # Store event in hash buckets
            event_data = self._serialize_event(event)

            for hash_key in hash_keys:
                self.redis_client.sadd(hash_key, event_data)
                self.redis_client.expire(hash_key, self.hash_ttl)

            # If duplicates found, return existing cluster ID or create new one
            if potential_duplicates:
                cluster_id = self._get_or_create_cluster(event, potential_duplicates)

                self.logger.log_data_processing(
                    operation="deduplication",
                    input_count=1,
                    output_count=0,  # Duplicate, no new output
                    processing_time=0,
                    event_id=event.id,
                    cluster_id=cluster_id,
                    duplicate_count=len(potential_duplicates),
                )

                return cluster_id
            else:
                # No duplicates, this is a unique event
                self.logger.log_data_processing(
                    operation="deduplication",
                    input_count=1,
                    output_count=1,  # Unique event
                    processing_time=0,
                    event_id=event.id,
                    status="unique",
                )

                return None

        except Exception as e:
            self.logger.error(
                f"Error adding event to LSH index: {e}", event_id=event.id
            )
            return None

    def _serialize_event(self, event: AccidentEvent) -> str:
        """Serialize event for storage in Redis"""
        return f"{event.id}|{event.source}|{event.lat}|{event.lon}|{event.timestamp}|{event.title}|{event.description}"

    def _deserialize_event(self, event_data: str) -> AccidentEvent:
        """Deserialize event from Redis storage"""
        parts = event_data.split("|", 6)
        if len(parts) != 7:
            raise ValueError(f"Invalid event data format: {event_data}")

        return AccidentEvent(
            id=parts[0],
            source=parts[1],
            lat=float(parts[2]),
            lon=float(parts[3]),
            timestamp=int(parts[4]),
            title=parts[5],
            description=parts[6],
            raw_data={},
        )

    def _get_or_create_cluster(
        self, event: AccidentEvent, duplicates: List[AccidentEvent]
    ) -> str:
        """Get existing cluster ID or create new cluster"""
        # Check if any duplicate already has a cluster ID
        for duplicate in duplicates:
            cluster_key = f"cluster:{duplicate.id}"
            cluster_id = self.redis_client.get(cluster_key)
            if cluster_id:
                # Add current event to existing cluster
                cluster_id = cluster_id.decode()
                self._add_to_cluster(cluster_id, event)
                return cluster_id

        # Create new cluster
        cluster_id = self._create_new_cluster(event, duplicates)
        return cluster_id

    def _create_new_cluster(
        self, primary_event: AccidentEvent, duplicates: List[AccidentEvent]
    ) -> str:
        """Create a new accident cluster"""
        cluster_id = f"cluster_{int(time.time() * 1000)}_{primary_event.id[:8]}"

        # Store cluster mapping for all events
        for event in [primary_event] + duplicates:
            cluster_key = f"cluster:{event.id}"
            self.redis_client.set(cluster_key, cluster_id, ex=self.hash_ttl)

        # Store cluster metadata
        cluster_data = {
            "cluster_id": cluster_id,
            "primary_event_id": primary_event.id,
            "event_count": len(duplicates) + 1,
            "created_at": datetime.utcnow().isoformat(),
            "sources": list({primary_event.source} | {d.source for d in duplicates}),
        }

        cluster_meta_key = f"cluster_meta:{cluster_id}"
        self.redis_client.hset(cluster_meta_key, mapping=cluster_data)
        self.redis_client.expire(cluster_meta_key, self.hash_ttl)

        return cluster_id

    def _add_to_cluster(self, cluster_id: str, event: AccidentEvent):
        """Add event to existing cluster"""
        # Update cluster mapping
        cluster_key = f"cluster:{event.id}"
        self.redis_client.set(cluster_key, cluster_id, ex=self.hash_ttl)

        # Update cluster metadata
        cluster_meta_key = f"cluster_meta:{cluster_id}"
        self.redis_client.hincrby(cluster_meta_key, "event_count", 1)
        self.redis_client.expire(cluster_meta_key, self.hash_ttl)

    def get_cluster_info(self, cluster_id: str) -> Optional[Dict]:
        """Get cluster information"""
        cluster_meta_key = f"cluster_meta:{cluster_id}"
        cluster_data = self.redis_client.hgetall(cluster_meta_key)

        if not cluster_data:
            return None

        return {k.decode(): v.decode() for k, v in cluster_data.items()}

    def cleanup_expired_data(self):
        """Clean up expired hash buckets and clusters"""
        try:
            # Redis TTL handles most cleanup automatically
            # This method can be used for additional cleanup logic if needed
            self.logger.info("Cleanup completed for expired deduplication data")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


class DeduplicationEngine:
    """Main deduplication engine that processes accident events"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.lsh = SpatialTemporalLSH(config)

    def process_event(self, event_data: Dict) -> Dict:
        """Process a single accident event for deduplication"""
        try:
            # Create AccidentEvent from input data
            event = AccidentEvent(
                id=event_data.get("id", ""),
                source=event_data.get("source", ""),
                lat=float(event_data.get("lat", 0)),
                lon=float(event_data.get("lon", 0)),
                timestamp=int(event_data.get("timestamp", 0)),
                title=event_data.get("title", ""),
                description=event_data.get("description", ""),
                raw_data=event_data,
            )

            # Process through LSH
            cluster_id = self.lsh.add_event(event)

            # Prepare output
            result = {
                "event_id": event.id,
                "source": event.source,
                "lat": event.lat,
                "lon": event.lon,
                "timestamp": event.timestamp,
                "title": event.title,
                "description": event.description,
                "is_duplicate": cluster_id is not None,
                "cluster_id": cluster_id,
                "processed_at": datetime.utcnow().isoformat(),
                "raw_data": event_data,
            }

            if cluster_id:
                cluster_info = self.lsh.get_cluster_info(cluster_id)
                if cluster_info:
                    result["cluster_info"] = cluster_info

            return result

        except Exception as e:
            self.logger.error(
                f"Error processing event for deduplication: {e}", event_data=event_data
            )

            # Return original data with error flag
            return {
                **event_data,
                "is_duplicate": False,
                "cluster_id": None,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def process_batch(self, events: List[Dict]) -> List[Dict]:
        """Process a batch of accident events"""
        results = []

        start_time = time.time()

        for event_data in events:
            result = self.process_event(event_data)
            results.append(result)

        processing_time = time.time() - start_time

        # Log batch processing metrics
        duplicates = sum(1 for r in results if r.get("is_duplicate", False))
        unique_events = len(results) - duplicates

        self.logger.log_data_processing(
            operation="batch_deduplication",
            input_count=len(events),
            output_count=unique_events,
            processing_time=processing_time,
            duplicate_count=duplicates,
            batch_size=len(events),
        )

        return results
