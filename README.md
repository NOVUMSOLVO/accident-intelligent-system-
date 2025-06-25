# Real-Time Accident Detection & Person Identification System

A comprehensive system for real-time accident detection, data aggregation, and person identification using multiple data sources and advanced processing pipelines.

## System Architecture

```
[Data Acquisition Layer] → [Stream Processing] → [Enrichment Engine] → [Output]
```

## Core Components

### 1. Accident Detection Module (Real-time)
- **Data Sources**: TomTom Traffic API, EMS/CAD feeds, Scanner Audio, Waze/Citizen APIs
- **Processing**: Apache Kafka for data ingestion
- **Deduplication**: Locality-sensitive hashing (LSH) for spatial-temporal deduplication
- **Clustering**: Accidents within 0.1mi radius/2min window

### 2. Person Identification Engine
- **License Plate Recognition**: Traffic camera APIs + OpenALPR
- **Reverse Lookup**: Registration data via DataTier/BeenVerified APIs
- **Graph Relationships**: Neo4j for vehicle-owner linkage
- **Phone Validation**: Twilio Lookup API

### 3. Social Media Scraping System
- **Platforms**: Facebook, Instagram, Twitter
- **Technology**: Scrapy-Redis cluster with rotating proxies
- **Compliance**: GDPR opt-out automation, request throttling

### 4. Real-time Processing Pipeline
- **Stream Processing**: Kafka → Spark Structured Streaming → MongoDB → Neo4j
- **Batch Processing**: 55-second micro-batches
- **Output**: 60-second CSV dumps to S3, webhook notifications

## Tech Stack

- **Message Broker**: Apache Kafka
- **Stream Processing**: Apache Spark Structured Streaming
- **Databases**: MongoDB (staging), Neo4j (relationships), Redis (caching)
- **APIs**: TomTom, OpenALPR, Twilio, Clearbit, PeopleDataLabs
- **Cloud Services**: AWS (Transcribe, KMS, S3)
- **Orchestration**: Apache Airflow
- **Web Scraping**: Scrapy, Selenium, Instaloader

## Project Structure

```
├── src/
│   ├── data_acquisition/     # Data ingestion modules
│   ├── stream_processing/    # Kafka and Spark components
│   ├── enrichment/          # Data enrichment services
│   ├── identification/      # Person identification logic
│   ├── social_scraping/     # Social media scrapers
│   └── output/              # Output generation
├── config/                  # Configuration files
├── docker/                  # Docker configurations
├── scripts/                 # Utility scripts
├── tests/                   # Test suites
└── docs/                    # Documentation
```

## Compliance & Ethics

- **Data Retention**: Maximum 90 days (Redis TTL)
- **Privacy**: CCPA/GDPR deletion automation
- **Security**: PII encryption with AWS KMS
- **Transparency**: Auto-generated opt-out links
- **Protected Classes**: Exclusion of first responders, government vehicles

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Configure environment variables in `.env`
3. Start services: `docker-compose up -d`
4. Run data pipeline: `python src/main.py`

## License

This project is for educational and research purposes only. Ensure compliance with all applicable laws and regulations.