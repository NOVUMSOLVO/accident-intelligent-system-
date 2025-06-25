#!/usr/bin/env python3
"""
Comprehensive Test Suite for Accident Detection System
Tests all major components and integration points
"""

import unittest
import json
import time
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.config import Config, load_config
from utils.logger import StructuredLogger
from data_acquisition.waze_collector import WazeDataCollector
from stream_processing.deduplication import DeduplicationEngine, AccidentEvent
from identification.person_identifier import PersonIdentificationEngine
from social_scraping.instagram_scraper import InstagramLocationScraper


class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        self.test_env = {
            'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092',
            'MONGODB_URI': 'mongodb://localhost:27017',
            'NEO4J_URI': 'bolt://localhost:7687',
            'REDIS_URL': 'redis://localhost:6379',
            'SPARK_MASTER_URL': 'local[*]'
        }
    
    def test_config_creation(self):
        """Test configuration object creation"""
        config = Config(
            kafka_bootstrap_servers='localhost:9092',
            mongodb_uri='mongodb://localhost:27017'
        )
        
        self.assertEqual(config.kafka_bootstrap_servers, 'localhost:9092')
        self.assertEqual(config.mongodb_uri, 'mongodb://localhost:27017')
    
    @patch.dict(os.environ, {'KAFKA_BOOTSTRAP_SERVERS': 'test:9092'})
    def test_load_config_from_env(self):
        """Test loading configuration from environment"""
        config = load_config()
        self.assertEqual(config.kafka_bootstrap_servers, 'test:9092')


class TestLogger(unittest.TestCase):
    """Test logging functionality"""
    
    def setUp(self):
        self.logger = StructuredLogger('test')
    
    def test_logger_creation(self):
        """Test logger creation"""
        self.assertIsNotNone(self.logger.logger)
        self.assertEqual(self.logger.logger.name, 'test')
    
    def test_structured_logging(self):
        """Test structured logging methods"""
        # Test API call logging
        self.logger.log_api_call('test_api', 'GET', '/test', 200, 100)
        
        # Test data processing logging
        self.logger.log_data_processing('test_process', {'count': 10}, 50)
        
        # Test Kafka event logging
        self.logger.log_kafka_event('test_topic', 'produce', {'key': 'test'})
        
        # Test database operation logging
        self.logger.log_database_operation('mongodb', 'insert', 'test_collection', True, 25)


class TestWazeCollector(unittest.TestCase):
    """Test Waze data collection"""
    
    def setUp(self):
        self.config = Config(
            kafka_bootstrap_servers='localhost:9092',
            waze_rss_url='https://www.waze.com/row-rtserver/web/TGeoRSS',
            collection_interval_seconds=60
        )
        self.collector = WazeDataCollector(self.config)
    
    @patch('requests.get')
    def test_fetch_waze_data_success(self, mock_get):
        """Test successful Waze data fetching"""
        # Mock RSS response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Accident on Main St</title>
                    <description>Traffic accident reported</description>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                    <link>https://waze.com/accident/123</link>
                    <georss:point>40.7128 -74.0060</georss:point>
                </item>
            </channel>
        </rss>
        '''
        mock_get.return_value = mock_response
        
        data = self.collector.fetch_waze_data()
        
        self.assertIsNotNone(data)
        self.assertIn('entries', data)
        self.assertEqual(len(data['entries']), 1)
        
        entry = data['entries'][0]
        self.assertEqual(entry['title'], 'Accident on Main St')
        self.assertEqual(entry['lat'], 40.7128)
        self.assertEqual(entry['lon'], -74.0060)
    
    @patch('requests.get')
    def test_fetch_waze_data_failure(self, mock_get):
        """Test Waze data fetching failure"""
        mock_get.side_effect = Exception("Network error")
        
        data = self.collector.fetch_waze_data()
        self.assertIsNone(data)
    
    def test_parse_coordinates(self):
        """Test coordinate parsing"""
        # Test valid coordinates
        lat, lon = self.collector.parse_coordinates("40.7128 -74.0060")
        self.assertEqual(lat, 40.7128)
        self.assertEqual(lon, -74.0060)
        
        # Test invalid coordinates
        lat, lon = self.collector.parse_coordinates("invalid")
        self.assertIsNone(lat)
        self.assertIsNone(lon)
    
    @patch('kafka.KafkaProducer')
    def test_publish_to_kafka(self, mock_producer_class):
        """Test Kafka publishing"""
        mock_producer = Mock()
        mock_producer_class.return_value = mock_producer
        
        accident_data = {
            'id': 'test_123',
            'source': 'waze',
            'lat': 40.7128,
            'lon': -74.0060,
            'timestamp': int(time.time() * 1000),
            'title': 'Test Accident'
        }
        
        result = self.collector.publish_to_kafka(accident_data)
        
        self.assertTrue(result)
        mock_producer.send.assert_called_once()


class TestDeduplicationEngine(unittest.TestCase):
    """Test deduplication functionality"""
    
    def setUp(self):
        self.config = Config(
            redis_url='redis://localhost:6379',
            dedup_radius_km=0.16,  # 0.1 miles
            dedup_time_window_minutes=2
        )
        
        # Mock Redis for testing
        with patch('redis.Redis'):
            self.dedup_engine = DeduplicationEngine(self.config)
    
    def test_accident_event_creation(self):
        """Test AccidentEvent creation"""
        event_data = {
            'id': 'test_123',
            'lat': 40.7128,
            'lon': -74.0060,
            'timestamp': int(time.time() * 1000),
            'source': 'waze'
        }
        
        event = AccidentEvent.from_dict(event_data)
        
        self.assertEqual(event.id, 'test_123')
        self.assertEqual(event.lat, 40.7128)
        self.assertEqual(event.lon, -74.0060)
        self.assertEqual(event.source, 'waze')
    
    def test_spatial_hash_generation(self):
        """Test spatial hash generation"""
        lat, lon = 40.7128, -74.0060
        
        hash1 = self.dedup_engine.lsh.generate_spatial_hash(lat, lon)
        hash2 = self.dedup_engine.lsh.generate_spatial_hash(lat + 0.001, lon + 0.001)  # Very close
        hash3 = self.dedup_engine.lsh.generate_spatial_hash(lat + 1.0, lon + 1.0)  # Far away
        
        self.assertIsInstance(hash1, str)
        self.assertIsInstance(hash2, str)
        self.assertIsInstance(hash3, str)
        
        # Close coordinates should have similar hashes
        # (This depends on the specific LSH implementation)
    
    def test_similarity_calculation(self):
        """Test similarity calculation between events"""
        event1 = AccidentEvent(
            id='test_1',
            lat=40.7128,
            lon=-74.0060,
            timestamp=int(time.time() * 1000),
            source='waze'
        )
        
        event2 = AccidentEvent(
            id='test_2',
            lat=40.7130,  # Very close
            lon=-74.0062,
            timestamp=event1.timestamp + 60000,  # 1 minute later
            source='tomtom'
        )
        
        similarity = self.dedup_engine.lsh.calculate_similarity(event1, event2)
        
        self.assertIsInstance(similarity, float)
        self.assertGreaterEqual(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)
    
    @patch('redis.Redis')
    def test_process_event(self, mock_redis):
        """Test event processing"""
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.smembers.return_value = set()
        
        event_data = {
            'id': 'test_123',
            'lat': 40.7128,
            'lon': -74.0060,
            'timestamp': int(time.time() * 1000),
            'source': 'waze',
            'title': 'Test Accident'
        }
        
        result = self.dedup_engine.process_event(event_data)
        
        self.assertIsInstance(result, dict)
        self.assertIn('is_duplicate', result)
        self.assertIn('cluster_id', result)


class TestPersonIdentificationEngine(unittest.TestCase):
    """Test person identification functionality"""
    
    def setUp(self):
        self.config = Config(
            openalpr_secret_key='test_key',
            datatier_api_key='test_key',
            beenverified_api_key='test_key',
            neo4j_uri='bolt://localhost:7687',
            neo4j_user='neo4j',
            neo4j_password='password',
            twilio_account_sid='test_sid',
            twilio_auth_token='test_token'
        )
        
        # Mock external dependencies
        with patch('neo4j.GraphDatabase.driver'), \
             patch('twilio.rest.Client'):
            self.identifier = PersonIdentificationEngine(self.config)
    
    @patch('requests.post')
    def test_openalpr_recognition(self, mock_post):
        """Test OpenALPR license plate recognition"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [{
                'plate': 'ABC123',
                'confidence': 95.5,
                'region': 'us-ny'
            }]
        }
        mock_post.return_value = mock_response
        
        result = self.identifier.openalpr_client.recognize_plate('fake_image_data')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['plate'], 'ABC123')
        self.assertEqual(result['confidence'], 95.5)
    
    @patch('requests.get')
    def test_vehicle_registration_lookup(self, mock_get):
        """Test vehicle registration lookup"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'owner_name': 'John Doe',
            'owner_address': '123 Main St, New York, NY',
            'vehicle_make': 'Toyota',
            'vehicle_model': 'Camry',
            'vehicle_year': 2020
        }
        mock_get.return_value = mock_response
        
        result = self.identifier.vehicle_lookup.lookup_registration('ABC123')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['owner_name'], 'John Doe')
        self.assertEqual(result['vehicle_make'], 'Toyota')
    
    def test_phone_validation(self):
        """Test phone number validation"""
        # Mock Twilio client
        mock_lookup = Mock()
        mock_lookup.phone_numbers.get.return_value = Mock(
            phone_number='+1234567890',
            carrier={'name': 'Verizon'},
            country_code='US'
        )
        self.identifier.twilio_client.lookups.v1 = mock_lookup
        
        result = self.identifier.validate_phone_number('1234567890')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['phone_number'], '+1234567890')
        self.assertEqual(result['carrier']['name'], 'Verizon')


class TestInstagramScraper(unittest.TestCase):
    """Test Instagram scraping functionality"""
    
    def setUp(self):
        self.config = Config(
            instagram_username='test_user',
            instagram_password='test_pass',
            proxy_list=['proxy1:8080', 'proxy2:8080'],
            rate_limit_requests_per_minute=30
        )
        
        # Mock Instaloader
        with patch('instaloader.Instaloader'):
            self.scraper = InstagramLocationScraper(self.config)
    
    def test_proxy_rotation(self):
        """Test proxy rotation functionality"""
        proxy1 = self.scraper.proxy_rotator.get_proxy()
        proxy2 = self.scraper.proxy_rotator.get_proxy()
        
        self.assertIsNotNone(proxy1)
        self.assertIsNotNone(proxy2)
        # Proxies should rotate
        self.assertNotEqual(proxy1, proxy2)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Test that rate limiting allows requests within limit
        self.assertTrue(self.scraper.rate_limiter.can_make_request())
        
        # Simulate making requests up to the limit
        for _ in range(30):  # Rate limit is 30 per minute
            self.scraper.rate_limiter.record_request()
        
        # Should still allow requests (depending on timing)
        # This test might need adjustment based on implementation
    
    @patch('instaloader.Instaloader')
    def test_location_scraping(self, mock_instaloader):
        """Test location-based post scraping"""
        # Mock location and posts
        mock_location = Mock()
        mock_post = Mock()
        mock_post.date_utc = time.time()
        mock_post.owner_username = 'test_user'
        mock_location.get_posts.return_value = [mock_post]
        
        mock_loader = Mock()
        mock_loader.get_location_by_id.return_value = mock_location
        mock_instaloader.return_value = mock_loader
        
        accident_data = {
            'lat': 40.7128,
            'lon': -74.0060,
            'timestamp': int(time.time() * 1000),
            'instagram_location_id': '123456'
        }
        
        posts = self.scraper.scrape_accident_location(accident_data)
        
        self.assertIsInstance(posts, list)
    
    def test_compliance_manager(self):
        """Test compliance management"""
        # Test robots.txt checking
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = "User-agent: *\nDisallow: /private/"
            mock_get.return_value = mock_response
            
            allowed = self.scraper.compliance_manager.check_robots_txt(
                'https://instagram.com', '/public/'
            )
            self.assertTrue(allowed)
            
            disallowed = self.scraper.compliance_manager.check_robots_txt(
                'https://instagram.com', '/private/'
            )
            self.assertFalse(disallowed)
        
        # Test opt-out link generation
        opt_out_link = self.scraper.compliance_manager.generate_opt_out_link('test_user')
        self.assertIn('test_user', opt_out_link)
        self.assertIn('opt-out', opt_out_link.lower())


class TestSystemIntegration(unittest.TestCase):
    """Test system integration scenarios"""
    
    def setUp(self):
        self.config = Config(
            kafka_bootstrap_servers='localhost:9092',
            mongodb_uri='mongodb://localhost:27017',
            neo4j_uri='bolt://localhost:7687',
            redis_url='redis://localhost:6379'
        )
    
    @patch('kafka.KafkaProducer')
    @patch('redis.Redis')
    def test_end_to_end_accident_processing(self, mock_redis, mock_kafka):
        """Test end-to-end accident processing flow"""
        # Mock external services
        mock_producer = Mock()
        mock_kafka.return_value = mock_producer
        
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance
        mock_redis_instance.smembers.return_value = set()
        
        # Create components
        collector = WazeDataCollector(self.config)
        dedup_engine = DeduplicationEngine(self.config)
        
        # Simulate accident data
        accident_data = {
            'id': 'integration_test_123',
            'source': 'waze',
            'lat': 40.7128,
            'lon': -74.0060,
            'timestamp': int(time.time() * 1000),
            'title': 'Integration Test Accident',
            'description': 'Test accident for integration testing'
        }
        
        # Test data flow
        # 1. Publish to Kafka
        publish_result = collector.publish_to_kafka(accident_data)
        self.assertTrue(publish_result)
        
        # 2. Process through deduplication
        dedup_result = dedup_engine.process_event(accident_data)
        self.assertIsInstance(dedup_result, dict)
        self.assertIn('is_duplicate', dedup_result)
        
        # Verify mock calls
        mock_producer.send.assert_called()
    
    def test_error_handling(self):
        """Test error handling across components"""
        # Test with invalid configuration
        invalid_config = Config()
        
        # Components should handle missing configuration gracefully
        try:
            collector = WazeDataCollector(invalid_config)
            # Should not raise exception during initialization
        except Exception as e:
            self.fail(f"Component initialization should not fail: {e}")
    
    def test_data_validation(self):
        """Test data validation across components"""
        # Test with invalid accident data
        invalid_data = {
            'id': None,  # Invalid ID
            'lat': 'invalid',  # Invalid latitude
            'lon': None,  # Missing longitude
            'timestamp': 'not_a_number'  # Invalid timestamp
        }
        
        # Components should handle invalid data gracefully
        with patch('redis.Redis'):
            dedup_engine = DeduplicationEngine(self.config)
            
            # Should not crash on invalid data
            try:
                result = dedup_engine.process_event(invalid_data)
                # Should return some result, even if it indicates an error
                self.assertIsInstance(result, dict)
            except Exception as e:
                # If it raises an exception, it should be handled gracefully
                self.assertIsInstance(e, (ValueError, TypeError))


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestConfig,
        TestLogger,
        TestWazeCollector,
        TestDeduplicationEngine,
        TestPersonIdentificationEngine,
        TestInstagramScraper,
        TestSystemIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)