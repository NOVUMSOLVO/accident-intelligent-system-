#!/usr/bin/env python3
"""
Waze Data Collector
Collects accident data from Waze RSS feed and publishes to Kafka
"""

import json

import feedparser
import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

from ..utils.config import Config
from ..utils.logger import get_logger


class WazeCollector:
    """Collects accident data from Waze RSS feeds"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        self.producer = self._init_kafka_producer()
        self.waze_url = "https://www.waze.com/row-rtserver/web/TGeoRSS"

    def _init_kafka_producer(self) -> KafkaProducer:
        """Initialize Kafka producer with error handling"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                acks="all",
                compression_type="gzip",
            )
            self.logger.info("Kafka producer initialized successfully")
            return producer
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def fetch_waze_data(self) -> Optional[Dict]:
        """Fetch data from Waze RSS feed"""
        try:
            response = requests.get(
                self.waze_url,
                timeout=30,
                headers={"User-Agent": "AccidentDetectionSystem/1.0"},
            )
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if feed.bozo:
                self.logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            return self._parse_feed_entries(feed.entries)

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch Waze data: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching Waze data: {e}")
            return None

    def _parse_feed_entries(self, entries: List) -> Dict:
        """Parse RSS feed entries and extract accident data"""
        accidents = []

        for entry in entries:
            try:
                # Extract coordinates from georss:point or other location fields
                coordinates = self._extract_coordinates(entry)
                if not coordinates:
                    continue

                # Check if this is an accident-related entry
                if self._is_accident_entry(entry):
                    accident_data = {
                        "source": "waze",
                        "id": entry.get("id", ""),
                        "title": entry.get("title", ""),
                        "description": entry.get("description", ""),
                        "lat": coordinates["lat"],
                        "lon": coordinates["lon"],
                        "timestamp": self._parse_timestamp(entry),
                        "pub_date": entry.get("published", ""),
                        "link": entry.get("link", ""),
                        "raw_entry": entry,
                    }
                    accidents.append(accident_data)

            except Exception as e:
                self.logger.warning(f"Failed to parse entry: {e}")
                continue

        return {
            "accidents": accidents,
            "total_count": len(accidents),
            "fetch_timestamp": datetime.utcnow().isoformat(),
        }

    def _extract_coordinates(self, entry: Dict) -> Optional[Dict[str, float]]:
        """Extract latitude and longitude from RSS entry"""
        # Try georss:point first
        if hasattr(entry, "georss_point"):
            try:
                lat, lon = map(float, entry.georss_point.split())
                return {"lat": lat, "lon": lon}
            except (ValueError, AttributeError):
                pass

        # Try other common location fields
        for field in ["geo_lat", "geo_long", "latitude", "longitude"]:
            if hasattr(entry, field):
                try:
                    if field in ["geo_lat", "latitude"]:
                        lat = float(getattr(entry, field))
                    else:
                        lon = float(getattr(entry, field))

                    if "lat" in locals() and "lon" in locals():
                        return {"lat": lat, "lon": lon}
                except (ValueError, AttributeError):
                    continue

        return None

    def _is_accident_entry(self, entry: Dict) -> bool:
        """Determine if RSS entry is accident-related"""
        accident_keywords = [
            "accident",
            "crash",
            "collision",
            "wreck",
            "incident",
            "emergency",
            "blocked",
            "closure",
            "traffic",
        ]

        text_to_check = " ".join(
            [
                entry.get("title", "").lower(),
                entry.get("description", "").lower(),
                entry.get("summary", "").lower(),
            ]
        )

        return any(keyword in text_to_check for keyword in accident_keywords)

    def _parse_timestamp(self, entry: Dict) -> int:
        """Parse timestamp from RSS entry"""
        try:
            # Try published_parsed first
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return int(time.mktime(entry.published_parsed) * 1000)

            # Try updated_parsed
            if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return int(time.mktime(entry.updated_parsed) * 1000)

            # Fallback to current time
            return int(time.time() * 1000)

        except Exception:
            return int(time.time() * 1000)

    def publish_to_kafka(self, data: Dict) -> bool:
        """Publish accident data to Kafka topic"""
        try:
            for accident in data.get("accidents", []):
                # Create message key for partitioning
                key = f"{accident['lat']:.4f},{accident['lon']:.4f}"

                # Send to Kafka
                future = self.producer.send(
                    self.config.kafka_topic_accidents_raw, key=key, value=accident
                )

                # Wait for confirmation (optional, can be async)
                record_metadata = future.get(timeout=10)

                self.logger.debug(
                    f"Published accident to topic {record_metadata.topic} "
                    f"partition {record_metadata.partition} "
                    f"offset {record_metadata.offset}"
                )

            self.logger.info(
                f"Published {len(data.get('accidents', []))} accidents to Kafka"
            )
            return True

        except KafkaError as e:
            self.logger.error(f"Kafka error publishing data: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error publishing to Kafka: {e}")
            return False

    def run_collection_cycle(self) -> bool:
        """Run a single data collection cycle"""
        self.logger.info("Starting Waze data collection cycle")

        # Fetch data from Waze
        waze_data = self.fetch_waze_data()
        if not waze_data:
            self.logger.warning("No data fetched from Waze")
            return False

        # Publish to Kafka
        success = self.publish_to_kafka(waze_data)

        if success:
            self.logger.info(
                f"Collection cycle completed successfully. "
                f"Processed {waze_data.get('total_count', 0)} accidents"
            )
        else:
            self.logger.error("Collection cycle failed during Kafka publishing")

        return success

    def run_continuous(self, interval_seconds: int = 60):
        """Run continuous data collection"""
        self.logger.info(
            f"Starting continuous Waze collection (interval: {interval_seconds}s)"
        )

        while True:
            try:
                self.run_collection_cycle()
                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, stopping collection")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in collection loop: {e}")
                time.sleep(interval_seconds)

    def close(self):
        """Clean up resources"""
        if self.producer:
            self.producer.close()
            self.logger.info("Kafka producer closed")


if __name__ == "__main__":
    from ..utils.config import load_config

    config = load_config()
    collector = WazeCollector(config)

    try:
        collector.run_continuous()
    finally:
        collector.close()
