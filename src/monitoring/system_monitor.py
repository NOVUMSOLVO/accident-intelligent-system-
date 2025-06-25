#!/usr/bin/env python3
"""
System Monitoring and Alerting
Monitors system health, performance metrics, and sends alerts
"""

import json
import threading
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

import psutil
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from ..utils.config import Config
from ..utils.logger import StructuredLogger


@dataclass
class SystemMetrics:
    """System performance metrics"""

    timestamp: int
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    process_count: int
    load_average: List[float]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class KafkaMetrics:
    """Kafka-specific metrics"""

    timestamp: int
    topic: str
    partition: int
    offset_lag: int
    messages_per_second: float
    error_rate: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""

    timestamp: int
    component: str
    accidents_processed: int
    duplicates_detected: int
    persons_identified: int
    social_profiles_found: int
    processing_latency_ms: float
    error_count: int

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Alert:
    """System alert"""

    timestamp: int
    severity: str  # 'info', 'warning', 'error', 'critical'
    component: str
    message: str
    metrics: Dict
    resolved: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


class MetricsCollector:
    """Collects system and application metrics"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        # Metrics storage
        self.system_metrics_history = deque(maxlen=1000)
        self.kafka_metrics_history = deque(maxlen=1000)
        self.app_metrics_history = deque(maxlen=1000)

        # Kafka consumer for monitoring
        self.kafka_consumer = None
        self.kafka_producer = None

        self._initialize_kafka()

    def _initialize_kafka(self):
        """Initialize Kafka consumer and producer for monitoring"""
        try:
            self.kafka_consumer = KafkaConsumer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="monitoring_group",
                value_deserializer=lambda x: (
                    json.loads(x.decode("utf-8")) if x else None
                ),
            )

            self.kafka_producer = KafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            )

            self.logger.info("Kafka monitoring initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka monitoring: {e}")

    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100

            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            }

            # Process count
            process_count = len(psutil.pids())

            # Load average (Unix-like systems)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                # Windows doesn't have load average
                load_average = [cpu_percent / 100.0] * 3

            metrics = SystemMetrics(
                timestamp=int(time.time() * 1000),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                process_count=process_count,
                load_average=load_average,
            )

            self.system_metrics_history.append(metrics)
            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return None

    def collect_kafka_metrics(self) -> List[KafkaMetrics]:
        """Collect Kafka-specific metrics"""
        metrics_list = []

        try:
            if not self.kafka_consumer:
                return metrics_list

            # Get topic partitions
            topics = [
                self.config.kafka_topic_accidents_raw,
                self.config.kafka_topic_accidents_processed,
            ]

            for topic in topics:
                try:
                    partitions = self.kafka_consumer.partitions_for_topic(topic)
                    if not partitions:
                        continue

                    for partition in partitions:
                        # Get partition metadata
                        tp = (topic, partition)

                        # Calculate lag (simplified)
                        try:
                            committed = self.kafka_consumer.committed(tp)
                            high_water = self.kafka_consumer.end_offsets([tp])[tp]
                            lag = high_water - (committed or 0)
                        except Exception:
                            lag = 0

                        metrics = KafkaMetrics(
                            timestamp=int(time.time() * 1000),
                            topic=topic,
                            partition=partition,
                            offset_lag=lag,
                            messages_per_second=0.0,  # Would need historical data
                            error_rate=0.0,  # Would need error tracking
                        )

                        metrics_list.append(metrics)
                        self.kafka_metrics_history.append(metrics)

                except Exception as e:
                    self.logger.error(
                        f"Error collecting metrics for topic {topic}: {e}"
                    )

            return metrics_list

        except Exception as e:
            self.logger.error(f"Error collecting Kafka metrics: {e}")
            return metrics_list

    def record_application_metrics(
        self, component: str, **kwargs
    ) -> ApplicationMetrics:
        """Record application-specific metrics"""
        try:
            metrics = ApplicationMetrics(
                timestamp=int(time.time() * 1000),
                component=component,
                accidents_processed=kwargs.get("accidents_processed", 0),
                duplicates_detected=kwargs.get("duplicates_detected", 0),
                persons_identified=kwargs.get("persons_identified", 0),
                social_profiles_found=kwargs.get("social_profiles_found", 0),
                processing_latency_ms=kwargs.get("processing_latency_ms", 0.0),
                error_count=kwargs.get("error_count", 0),
            )

            self.app_metrics_history.append(metrics)

            # Publish to Kafka for real-time monitoring
            if self.kafka_producer:
                try:
                    self.kafka_producer.send(
                        "system_metrics",
                        value={
                            "type": "application_metrics",
                            "data": metrics.to_dict(),
                        },
                    )
                except Exception as e:
                    self.logger.error(f"Failed to publish application metrics: {e}")

            return metrics

        except Exception as e:
            self.logger.error(f"Error recording application metrics: {e}")
            return None

    def get_metrics_summary(self, minutes: int = 5) -> Dict:
        """Get metrics summary for the last N minutes"""
        cutoff_time = int((time.time() - minutes * 60) * 1000)

        # Filter recent metrics
        recent_system = [
            m for m in self.system_metrics_history if m.timestamp > cutoff_time
        ]
        recent_kafka = [
            m for m in self.kafka_metrics_history if m.timestamp > cutoff_time
        ]
        recent_app = [m for m in self.app_metrics_history if m.timestamp > cutoff_time]

        summary = {
            "time_range_minutes": minutes,
            "system": {
                "avg_cpu_percent": (
                    sum(m.cpu_percent for m in recent_system) / len(recent_system)
                    if recent_system
                    else 0
                ),
                "avg_memory_percent": (
                    sum(m.memory_percent for m in recent_system) / len(recent_system)
                    if recent_system
                    else 0
                ),
                "avg_disk_percent": (
                    sum(m.disk_percent for m in recent_system) / len(recent_system)
                    if recent_system
                    else 0
                ),
                "sample_count": len(recent_system),
            },
            "kafka": {
                "total_lag": sum(m.offset_lag for m in recent_kafka),
                "topics_monitored": len(set(m.topic for m in recent_kafka)),
                "sample_count": len(recent_kafka),
            },
            "application": {
                "total_accidents_processed": sum(
                    m.accidents_processed for m in recent_app
                ),
                "total_duplicates_detected": sum(
                    m.duplicates_detected for m in recent_app
                ),
                "total_persons_identified": sum(
                    m.persons_identified for m in recent_app
                ),
                "total_errors": sum(m.error_count for m in recent_app),
                "avg_latency_ms": (
                    sum(m.processing_latency_ms for m in recent_app) / len(recent_app)
                    if recent_app
                    else 0
                ),
                "sample_count": len(recent_app),
            },
        }

        return summary


class AlertManager:
    """Manages system alerts and notifications"""

    def __init__(self, config: Config, metrics_collector: MetricsCollector):
        self.config = config
        self.metrics_collector = metrics_collector
        self.logger = StructuredLogger(__name__)

        # Alert storage
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)

        # Alert thresholds
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "kafka_lag": 1000,
            "error_rate": 0.05,
            "processing_latency_ms": 5000.0,
        }

        # Notification channels
        self.notification_channels = []
        self._setup_notification_channels()

    def _setup_notification_channels(self):
        """Setup notification channels"""
        # Webhook notifications
        if hasattr(self.config, "webhook_url") and self.config.webhook_url:
            self.notification_channels.append(self._send_webhook_notification)

        # Email notifications (would need SMTP configuration)
        # Slack notifications (would need Slack webhook)
        # etc.

    def check_system_alerts(self, metrics: SystemMetrics) -> List[Alert]:
        """Check for system-level alerts"""
        alerts = []

        # CPU usage alert
        if metrics.cpu_percent > self.thresholds["cpu_percent"]:
            alert = Alert(
                timestamp=metrics.timestamp,
                severity="warning" if metrics.cpu_percent < 95 else "critical",
                component="system",
                message=f"High CPU usage: {metrics.cpu_percent:.1f}%",
                metrics={"cpu_percent": metrics.cpu_percent},
            )
            alerts.append(alert)

        # Memory usage alert
        if metrics.memory_percent > self.thresholds["memory_percent"]:
            alert = Alert(
                timestamp=metrics.timestamp,
                severity="warning" if metrics.memory_percent < 95 else "critical",
                component="system",
                message=f"High memory usage: {metrics.memory_percent:.1f}%",
                metrics={"memory_percent": metrics.memory_percent},
            )
            alerts.append(alert)

        # Disk usage alert
        if metrics.disk_percent > self.thresholds["disk_percent"]:
            alert = Alert(
                timestamp=metrics.timestamp,
                severity="warning" if metrics.disk_percent < 98 else "critical",
                component="system",
                message=f"High disk usage: {metrics.disk_percent:.1f}%",
                metrics={"disk_percent": metrics.disk_percent},
            )
            alerts.append(alert)

        return alerts

    def check_kafka_alerts(self, metrics_list: List[KafkaMetrics]) -> List[Alert]:
        """Check for Kafka-related alerts"""
        alerts = []

        for metrics in metrics_list:
            # Kafka lag alert
            if metrics.offset_lag > self.thresholds["kafka_lag"]:
                alert = Alert(
                    timestamp=metrics.timestamp,
                    severity="warning" if metrics.offset_lag < 5000 else "error",
                    component="kafka",
                    message=f"High Kafka lag on {metrics.topic}:{metrics.partition}: {metrics.offset_lag}",
                    metrics={
                        "topic": metrics.topic,
                        "partition": metrics.partition,
                        "lag": metrics.offset_lag,
                    },
                )
                alerts.append(alert)

        return alerts

    def check_application_alerts(self, metrics: ApplicationMetrics) -> List[Alert]:
        """Check for application-specific alerts"""
        alerts = []

        # High processing latency
        if metrics.processing_latency_ms > self.thresholds["processing_latency_ms"]:
            alert = Alert(
                timestamp=metrics.timestamp,
                severity="warning",
                component=metrics.component,
                message=f"High processing latency in {metrics.component}: {metrics.processing_latency_ms:.1f}ms",
                metrics={
                    "component": metrics.component,
                    "latency_ms": metrics.processing_latency_ms,
                },
            )
            alerts.append(alert)

        # Error rate alert
        if metrics.error_count > 0:
            alert = Alert(
                timestamp=metrics.timestamp,
                severity="error",
                component=metrics.component,
                message=f"Errors detected in {metrics.component}: {metrics.error_count}",
                metrics={
                    "component": metrics.component,
                    "error_count": metrics.error_count,
                },
            )
            alerts.append(alert)

        return alerts

    def process_alert(self, alert: Alert):
        """Process and potentially send an alert"""
        alert_key = f"{alert.component}_{alert.severity}_{hash(alert.message)}"

        # Check if this is a duplicate alert (within 5 minutes)
        if alert_key in self.active_alerts:
            last_alert_time = self.active_alerts[alert_key].timestamp
            if alert.timestamp - last_alert_time < 300000:  # 5 minutes in ms
                return  # Skip duplicate alert

        # Store alert
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)

        # Log alert
        self.logger.warning(f"ALERT: {alert.message}", extra={"alert": alert.to_dict()})

        # Send notifications
        for channel in self.notification_channels:
            try:
                channel(alert)
            except Exception as e:
                self.logger.error(f"Failed to send alert notification: {e}")

    def _send_webhook_notification(self, alert: Alert):
        """Send alert via webhook"""
        try:
            payload = {
                "timestamp": alert.timestamp,
                "severity": alert.severity,
                "component": alert.component,
                "message": alert.message,
                "metrics": alert.metrics,
                "system": "accident_detection_system",
            }

            response = requests.post(self.config.webhook_url, json=payload, timeout=10)

            if response.status_code == 200:
                self.logger.info(f"Alert notification sent via webhook")
            else:
                self.logger.error(
                    f"Webhook notification failed: {response.status_code}"
                )

        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get currently active alerts"""
        # Clean up old alerts (older than 1 hour)
        current_time = int(time.time() * 1000)
        cutoff_time = current_time - 3600000  # 1 hour

        active_alerts = []
        for key, alert in list(self.active_alerts.items()):
            if alert.timestamp > cutoff_time:
                active_alerts.append(alert)
            else:
                del self.active_alerts[key]

        return active_alerts


class SystemMonitor:
    """Main system monitoring orchestrator"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        # Initialize components
        self.metrics_collector = MetricsCollector(config)
        self.alert_manager = AlertManager(config, self.metrics_collector)

        # Monitoring control
        self.running = False
        self.monitor_thread = None

        # Monitoring intervals
        self.system_metrics_interval = 30  # seconds
        self.kafka_metrics_interval = 60  # seconds
        self.alert_check_interval = 30  # seconds

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.running:
            self.logger.warning("Monitoring already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitor_thread.start()

        self.logger.info("System monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)

        self.logger.info("System monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        last_system_check = 0
        last_kafka_check = 0
        last_alert_check = 0

        while self.running:
            try:
                current_time = time.time()

                # Collect system metrics
                if current_time - last_system_check >= self.system_metrics_interval:
                    system_metrics = self.metrics_collector.collect_system_metrics()
                    if system_metrics:
                        # Check for system alerts
                        alerts = self.alert_manager.check_system_alerts(system_metrics)
                        for alert in alerts:
                            self.alert_manager.process_alert(alert)

                    last_system_check = current_time

                # Collect Kafka metrics
                if current_time - last_kafka_check >= self.kafka_metrics_interval:
                    kafka_metrics = self.metrics_collector.collect_kafka_metrics()
                    if kafka_metrics:
                        # Check for Kafka alerts
                        alerts = self.alert_manager.check_kafka_alerts(kafka_metrics)
                        for alert in alerts:
                            self.alert_manager.process_alert(alert)

                    last_kafka_check = current_time

                # General alert processing
                if current_time - last_alert_check >= self.alert_check_interval:
                    # Log system status
                    summary = self.metrics_collector.get_metrics_summary(5)
                    self.logger.info(
                        "System status", extra={"metrics_summary": summary}
                    )

                    last_alert_check = current_time

                # Sleep for a short interval
                time.sleep(5)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer on error

    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            "monitoring_active": self.running,
            "metrics_summary": self.metrics_collector.get_metrics_summary(10),
            "active_alerts": [
                alert.to_dict() for alert in self.alert_manager.get_active_alerts()
            ],
            "timestamp": int(time.time() * 1000),
        }

    def record_application_event(self, component: str, **kwargs):
        """Record an application event for monitoring"""
        metrics = self.metrics_collector.record_application_metrics(component, **kwargs)
        if metrics:
            # Check for application alerts
            alerts = self.alert_manager.check_application_alerts(metrics)
            for alert in alerts:
                self.alert_manager.process_alert(alert)


if __name__ == "__main__":
    from ..utils.config import load_config

    # Load configuration
    config = load_config()

    # Create and start monitor
    monitor = SystemMonitor(config)

    try:
        monitor.start_monitoring()

        # Keep running
        while True:
            time.sleep(60)
            status = monitor.get_system_status()
            print(f"System Status: {json.dumps(status, indent=2)}")

    except KeyboardInterrupt:
        print("\nShutting down monitoring...")
    finally:
        monitor.stop_monitoring()
