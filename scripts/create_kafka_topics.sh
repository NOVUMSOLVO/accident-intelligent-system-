#!/bin/bash
# Create Kafka topics for accident detection system

echo "Creating Kafka topics..."

# Wait for Kafka to be ready
sleep 30

# Create topics
docker-compose exec kafka kafka-topics.sh --create --topic accidents-raw --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic accidents-processed --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic accidents-enriched --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics.sh --create --topic social-profiles --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

echo "Kafka topics created successfully!"
