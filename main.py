#!/usr/bin/env python3
"""
Main Application Entry Point
Real-Time Accident Detection & Person Identification System
"""

import os
import sys
import signal
import threading
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config import load_config, validate_config
from src.utils.logger import StructuredLogger
from src.data_acquisition.waze_collector import WazeDataCollector
from src.stream_processing.spark_processor import SparkAccidentProcessor
from src.identification.person_identifier import PersonIdentificationEngine
from src.social_scraping.instagram_scraper import InstagramLocationScraper


class AccidentDetectionSystem:
    """Main orchestrator for the accident detection system"""
    
    def __init__(self):
        # Load configuration
        self.config = load_config()
        validate_config(self.config)
        
        # Initialize logger
        self.logger = StructuredLogger(__name__)
        
        # Initialize components
        self.components = {}
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="AccidentSystem")
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("Accident Detection System initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize_components(self):
        """Initialize all system components"""
        try:
            self.logger.info("Initializing system components...")
            
            # Initialize data collectors
            self.components['waze_collector'] = WazeDataCollector(self.config)
            
            # Initialize stream processor
            self.components['spark_processor'] = SparkAccidentProcessor(self.config)
            
            # Initialize identification engine
            self.components['person_identifier'] = PersonIdentificationEngine(self.config)
            
            # Initialize social scraper
            self.components['instagram_scraper'] = InstagramLocationScraper(self.config)
            
            self.logger.info("All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def start_data_collection(self):
        """Start data collection components"""
        try:
            self.logger.info("Starting data collection...")
            
            # Start Waze collector
            waze_future = self.executor.submit(
                self.components['waze_collector'].start_collection
            )
            
            # Monitor collection status
            def monitor_collection():
                while not self.shutdown_event.is_set():
                    try:
                        if waze_future.done():
                            result = waze_future.result(timeout=1)
                            if result:
                                self.logger.info("Waze collection completed successfully")
                            else:
                                self.logger.warning("Waze collection completed with issues")
                            break
                    except Exception as e:
                        self.logger.error(f"Error monitoring collection: {e}")
                        break
                    
                    time.sleep(30)  # Check every 30 seconds
            
            # Start monitoring in background
            self.executor.submit(monitor_collection)
            
            self.logger.info("Data collection started")
            
        except Exception as e:
            self.logger.error(f"Failed to start data collection: {e}")
            raise
    
    def start_stream_processing(self):
        """Start stream processing pipeline"""
        try:
            self.logger.info("Starting stream processing pipeline...")
            
            # Start Spark processor in background
            spark_future = self.executor.submit(
                self.components['spark_processor'].run_processing_pipeline
            )
            
            # Monitor processing status
            def monitor_processing():
                while not self.shutdown_event.is_set():
                    try:
                        if spark_future.done():
                            result = spark_future.result(timeout=1)
                            self.logger.info("Stream processing completed")
                            break
                    except Exception as e:
                        self.logger.error(f"Error in stream processing: {e}")
                        # Restart processing if it fails
                        if not self.shutdown_event.is_set():
                            self.logger.info("Restarting stream processing...")
                            time.sleep(10)
                            self.start_stream_processing()
                        break
                    
                    time.sleep(60)  # Check every minute
            
            # Start monitoring in background
            self.executor.submit(monitor_processing)
            
            self.logger.info("Stream processing started")
            
        except Exception as e:
            self.logger.error(f"Failed to start stream processing: {e}")
            raise
    
    def start_health_monitoring(self):
        """Start system health monitoring"""
        try:
            self.logger.info("Starting health monitoring...")
            
            def health_check():
                while not self.shutdown_event.is_set():
                    try:
                        # Check component health
                        health_status = {
                            'timestamp': int(time.time() * 1000),
                            'components': {}
                        }
                        
                        # Check Waze collector
                        if 'waze_collector' in self.components:
                            health_status['components']['waze_collector'] = 'running'
                        
                        # Check Spark processor
                        if 'spark_processor' in self.components:
                            health_status['components']['spark_processor'] = 'running'
                        
                        # Log health status
                        self.logger.info("System health check", extra={
                            'health_status': health_status
                        })
                        
                        # Wait before next check
                        self.shutdown_event.wait(300)  # 5 minutes
                        
                    except Exception as e:
                        self.logger.error(f"Error in health monitoring: {e}")
                        self.shutdown_event.wait(60)  # Wait 1 minute on error
            
            # Start health monitoring in background
            self.executor.submit(health_check)
            
            self.logger.info("Health monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start health monitoring: {e}")
    
    def run(self):
        """Run the complete accident detection system"""
        try:
            self.logger.info("Starting Accident Detection System...")
            
            # Initialize all components
            self.initialize_components()
            
            # Mark system as running
            self.running = True
            
            # Start data collection
            self.start_data_collection()
            
            # Wait a bit for data collection to start
            time.sleep(10)
            
            # Start stream processing
            self.start_stream_processing()
            
            # Start health monitoring
            self.start_health_monitoring()
            
            self.logger.info("All systems started successfully")
            
            # Keep main thread alive
            while self.running and not self.shutdown_event.is_set():
                try:
                    self.shutdown_event.wait(60)  # Check every minute
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt")
                    break
            
        except Exception as e:
            self.logger.error(f"Error running system: {e}")
            raise
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the system"""
        if not self.running:
            return
        
        try:
            self.logger.info("Shutting down Accident Detection System...")
            
            # Signal shutdown to all components
            self.shutdown_event.set()
            self.running = False
            
            # Stop components
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'stop'):
                        self.logger.info(f"Stopping {name}...")
                        component.stop()
                    elif hasattr(component, 'close'):
                        self.logger.info(f"Closing {name}...")
                        component.close()
                    elif hasattr(component, 'cleanup'):
                        self.logger.info(f"Cleaning up {name}...")
                        component.cleanup()
                except Exception as e:
                    self.logger.error(f"Error stopping {name}: {e}")
            
            # Shutdown executor
            try:
                self.executor.shutdown(wait=True, timeout=30)
            except Exception as e:
                self.logger.error(f"Error shutting down executor: {e}")
            
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        return {
            'running': self.running,
            'components': list(self.components.keys()),
            'config': {
                'kafka_servers': self.config.kafka_bootstrap_servers,
                'spark_master': self.config.spark_master_url,
                'debug_mode': self.config.debug
            }
        }


def main():
    """Main entry point"""
    print("="*60)
    print("Real-Time Accident Detection & Person Identification System")
    print("="*60)
    
    system = None
    try:
        # Create and run system
        system = AccidentDetectionSystem()
        
        # Print system status
        status = system.get_system_status()
        print(f"\nSystem Configuration:")
        print(f"  Kafka Servers: {status['config']['kafka_servers']}")
        print(f"  Spark Master: {status['config']['spark_master']}")
        print(f"  Debug Mode: {status['config']['debug_mode']}")
        print(f"\nStarting system...\n")
        
        # Run the system
        system.run()
        
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"\nSystem error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if system:
            system.shutdown()
        print("\nSystem stopped.")


if __name__ == "__main__":
    main()