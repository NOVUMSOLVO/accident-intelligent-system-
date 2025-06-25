#!/usr/bin/env python3
"""
Configuration Management
Handles environment variables and application settings
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration class"""

    # API Keys
    tomtom_api_key: str
    openalpr_secret_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    google_maps_api_key: str
    clearbit_api_key: str
    people_data_labs_api_key: str
    datatier_api_key: str
    been_verified_api_key: str

    # AWS Configuration
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    aws_s3_bucket: str
    aws_kms_key_id: str

    # Database Configuration
    mongodb_uri: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    redis_url: str
    postgres_uri: str

    # Kafka Configuration
    kafka_bootstrap_servers: str
    kafka_topic_accidents_raw: str
    kafka_topic_accidents_processed: str
    kafka_topic_person_data: str
    kafka_topic_social_data: str

    # Spark Configuration
    spark_master_url: str
    spark_app_name: str

    # Proxy Configuration
    proxy_provider: str
    proxy_username: str
    proxy_password: str
    proxy_endpoint: str

    # Rate Limiting
    request_throttle_seconds: int
    api_rate_limit_per_minute: int

    # Data Retention
    data_retention_days: int
    redis_ttl_seconds: int

    # Compliance
    gdpr_compliance_enabled: bool
    ccpa_compliance_enabled: bool
    opt_out_webhook_url: str

    # Logging
    log_level: str
    log_format: str

    # Security
    encryption_enabled: bool
    secret_key: str
    jwt_secret_key: str

    # Monitoring
    prometheus_enabled: bool
    prometheus_port: int
    grafana_enabled: bool
    grafana_port: int

    # Application Settings
    flask_env: str
    debug: bool
    port: int
    host: str

    # Deduplication Settings
    deduplication_radius_miles: float
    deduplication_time_window_minutes: int

    # Processing Settings
    micro_batch_duration_seconds: int
    output_interval_seconds: int
    window_duration_minutes: int


def load_config() -> Config:
    """Load configuration from environment variables"""
    # Load .env file if it exists
    load_dotenv()

    def get_env(key: str, default: Optional[str] = None, required: bool = True) -> str:
        """Get environment variable with validation"""
        value = os.getenv(key, default)
        if required and value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def get_env_bool(key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def get_env_int(key: str, default: int = 0) -> int:
        """Get integer environment variable"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def get_env_float(key: str, default: float = 0.0) -> float:
        """Get float environment variable"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default

    return Config(
        # API Keys
        tomtom_api_key=get_env("TOMTOM_API_KEY", required=False),
        openalpr_secret_key=get_env("OPENALPR_SECRET_KEY", required=False),
        twilio_account_sid=get_env("TWILIO_ACCOUNT_SID", required=False),
        twilio_auth_token=get_env("TWILIO_AUTH_TOKEN", required=False),
        google_maps_api_key=get_env("GOOGLE_MAPS_API_KEY", required=False),
        clearbit_api_key=get_env("CLEARBIT_API_KEY", required=False),
        people_data_labs_api_key=get_env("PEOPLE_DATA_LABS_API_KEY", required=False),
        datatier_api_key=get_env("DATATIER_API_KEY", required=False),
        been_verified_api_key=get_env("BEEN_VERIFIED_API_KEY", required=False),
        # AWS Configuration
        aws_access_key_id=get_env("AWS_ACCESS_KEY_ID", required=False),
        aws_secret_access_key=get_env("AWS_SECRET_ACCESS_KEY", required=False),
        aws_region=get_env("AWS_REGION", "us-east-1"),
        aws_s3_bucket=get_env("AWS_S3_BUCKET", "accident-detection-data"),
        aws_kms_key_id=get_env("AWS_KMS_KEY_ID", required=False),
        # Database Configuration
        mongodb_uri=get_env("MONGODB_URI", "mongodb://admin:password@localhost:27017"),
        neo4j_uri=get_env("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=get_env("NEO4J_USER", "neo4j"),
        neo4j_password=get_env("NEO4J_PASSWORD", "password"),
        redis_url=get_env("REDIS_URL", "redis://localhost:6379"),
        postgres_uri=get_env(
            "POSTGRES_URI", "postgresql://airflow:airflow@localhost:5432/airflow"
        ),
        # Kafka Configuration
        kafka_bootstrap_servers=get_env("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic_accidents_raw=get_env("KAFKA_TOPIC_ACCIDENTS_RAW", "accidents-raw"),
        kafka_topic_accidents_processed=get_env(
            "KAFKA_TOPIC_ACCIDENTS_PROCESSED", "accidents-processed"
        ),
        kafka_topic_person_data=get_env("KAFKA_TOPIC_PERSON_DATA", "person-data"),
        kafka_topic_social_data=get_env("KAFKA_TOPIC_SOCIAL_DATA", "social-data"),
        # Spark Configuration
        spark_master_url=get_env("SPARK_MASTER_URL", "spark://localhost:7077"),
        spark_app_name=get_env("SPARK_APP_NAME", "AccidentDetectionSystem"),
        # Proxy Configuration
        proxy_provider=get_env("PROXY_PROVIDER", "brightdata"),
        proxy_username=get_env("PROXY_USERNAME", required=False),
        proxy_password=get_env("PROXY_PASSWORD", required=False),
        proxy_endpoint=get_env("PROXY_ENDPOINT", required=False),
        # Rate Limiting
        request_throttle_seconds=get_env_int("REQUEST_THROTTLE_SECONDS", 120),
        api_rate_limit_per_minute=get_env_int("API_RATE_LIMIT_PER_MINUTE", 60),
        # Data Retention
        data_retention_days=get_env_int("DATA_RETENTION_DAYS", 90),
        redis_ttl_seconds=get_env_int("REDIS_TTL_SECONDS", 7776000),
        # Compliance
        gdpr_compliance_enabled=get_env_bool("GDPR_COMPLIANCE_ENABLED", True),
        ccpa_compliance_enabled=get_env_bool("CCPA_COMPLIANCE_ENABLED", True),
        opt_out_webhook_url=get_env("OPT_OUT_WEBHOOK_URL", required=False),
        # Logging
        log_level=get_env("LOG_LEVEL", "INFO"),
        log_format=get_env("LOG_FORMAT", "json"),
        # Security
        encryption_enabled=get_env_bool("ENCRYPTION_ENABLED", True),
        secret_key=get_env("SECRET_KEY", required=False),
        jwt_secret_key=get_env("JWT_SECRET_KEY", required=False),
        # Monitoring
        prometheus_enabled=get_env_bool("PROMETHEUS_ENABLED", True),
        prometheus_port=get_env_int("PROMETHEUS_PORT", 9090),
        grafana_enabled=get_env_bool("GRAFANA_ENABLED", True),
        grafana_port=get_env_int("GRAFANA_PORT", 3000),
        # Application Settings
        flask_env=get_env("FLASK_ENV", "development"),
        debug=get_env_bool("DEBUG", True),
        port=get_env_int("PORT", 5000),
        host=get_env("HOST", "0.0.0.0"),
        # Deduplication Settings
        deduplication_radius_miles=get_env_float("DEDUPLICATION_RADIUS_MILES", 0.1),
        deduplication_time_window_minutes=get_env_int(
            "DEDUPLICATION_TIME_WINDOW_MINUTES", 2
        ),
        # Processing Settings
        micro_batch_duration_seconds=get_env_int("MICRO_BATCH_DURATION_SECONDS", 55),
        output_interval_seconds=get_env_int("OUTPUT_INTERVAL_SECONDS", 60),
        window_duration_minutes=get_env_int("WINDOW_DURATION_MINUTES", 5),
    )


def validate_config(config: Config) -> List[str]:
    """Validate configuration and return list of errors"""
    errors = []

    # Check required API keys for production
    if config.flask_env == "production":
        required_keys = [
            ("tomtom_api_key", "TOMTOM_API_KEY"),
            ("google_maps_api_key", "GOOGLE_MAPS_API_KEY"),
            ("secret_key", "SECRET_KEY"),
            ("jwt_secret_key", "JWT_SECRET_KEY"),
        ]

        for attr, env_var in required_keys:
            if not getattr(config, attr):
                errors.append(
                    f"Required configuration {env_var} is missing for production"
                )

    # Validate numeric ranges
    if config.deduplication_radius_miles <= 0:
        errors.append("Deduplication radius must be positive")

    if config.deduplication_time_window_minutes <= 0:
        errors.append("Deduplication time window must be positive")

    if config.micro_batch_duration_seconds <= 0:
        errors.append("Micro batch duration must be positive")

    return errors
