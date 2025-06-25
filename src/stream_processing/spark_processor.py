#!/usr/bin/env python3
"""
Spark Structured Streaming Processor
Processes accident data through Kafka → Spark → MongoDB → Neo4j pipeline
"""

import json

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    collect_list,
    count,
    expr,
    from_json,
    lit,
    struct,
    to_json,
    udf,
    when,
    window,
)
from pyspark.sql.streaming import StreamingQuery
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from ..identification.person_identifier import PersonIdentificationEngine
from ..social_scraping.instagram_scraper import InstagramLocationScraper
from ..utils.config import Config
from ..utils.logger import StructuredLogger
from .deduplication import DeduplicationEngine


class SparkAccidentProcessor:
    """Main Spark processor for accident detection pipeline"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        # Initialize Spark session
        self.spark = self._create_spark_session()

        # Initialize processing engines
        self.deduplication_engine = DeduplicationEngine(config)
        self.person_identifier = PersonIdentificationEngine(config)
        self.instagram_scraper = InstagramLocationScraper(config)

        # Define schemas
        self.accident_schema = self._define_accident_schema()
        self.enriched_schema = self._define_enriched_schema()

    def _create_spark_session(self) -> SparkSession:
        """Create and configure Spark session"""
        try:
            spark = (
                SparkSession.builder.appName(self.config.spark_app_name)
                .master(self.config.spark_master_url)
                .config("spark.sql.streaming.checkpointLocation", "./checkpoints")
                .config("spark.sql.streaming.stateStore.maintenanceInterval", "60s")
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
                .config(
                    "spark.serializer", "org.apache.spark.serializer.KryoSerializer"
                )
                .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true")
                .getOrCreate()
            )

            # Set log level
            spark.sparkContext.setLogLevel("WARN")

            self.logger.info("Spark session created successfully")
            return spark

        except Exception as e:
            self.logger.error(f"Failed to create Spark session: {e}")
            raise

    def _define_accident_schema(self) -> StructType:
        """Define schema for incoming accident data"""
        return StructType(
            [
                StructField("id", StringType(), True),
                StructField("source", StringType(), True),
                StructField("lat", DoubleType(), True),
                StructField("lon", DoubleType(), True),
                StructField("timestamp", LongType(), True),
                StructField("title", StringType(), True),
                StructField("description", StringType(), True),
                StructField("pub_date", StringType(), True),
                StructField("link", StringType(), True),
                StructField("raw_entry", StringType(), True),
            ]
        )

    def _define_enriched_schema(self) -> StructType:
        """Define schema for enriched accident data"""
        return StructType(
            [
                StructField("accident_id", StringType(), True),
                StructField("source", StringType(), True),
                StructField("lat", DoubleType(), True),
                StructField("lon", DoubleType(), True),
                StructField("timestamp", LongType(), True),
                StructField("title", StringType(), True),
                StructField("description", StringType(), True),
                StructField("is_duplicate", BooleanType(), True),
                StructField("cluster_id", StringType(), True),
                StructField("identified_persons", ArrayType(StringType()), True),
                StructField("social_profiles", ArrayType(StringType()), True),
                StructField("confidence_score", DoubleType(), True),
                StructField("processing_timestamp", LongType(), True),
            ]
        )

    def create_kafka_stream(self, topic: str) -> DataFrame:
        """Create Kafka streaming DataFrame"""
        try:
            df = (
                self.spark.readStream.format("kafka")
                .option("kafka.bootstrap.servers", self.config.kafka_bootstrap_servers)
                .option("subscribe", topic)
                .option("startingOffsets", "latest")
                .option("failOnDataLoss", "false")
                .option("maxOffsetsPerTrigger", 1000)
                .load()
            )

            self.logger.info(f"Created Kafka stream for topic: {topic}")
            return df

        except Exception as e:
            self.logger.error(f"Failed to create Kafka stream: {e}")
            raise

    def parse_accident_data(self, kafka_df: DataFrame) -> DataFrame:
        """Parse JSON accident data from Kafka"""
        try:
            # Parse JSON from Kafka value
            parsed_df = (
                kafka_df.select(
                    col("key").cast("string").alias("kafka_key"),
                    col("topic"),
                    col("partition"),
                    col("offset"),
                    col("timestamp").alias("kafka_timestamp"),
                    from_json(col("value").cast("string"), self.accident_schema).alias(
                        "data"
                    ),
                )
                .select(
                    col("kafka_key"),
                    col("topic"),
                    col("partition"),
                    col("offset"),
                    col("kafka_timestamp"),
                    col("data.*"),
                )
                .filter(col("id").isNotNull())
            )

            self.logger.info("Parsed accident data from Kafka")
            return parsed_df

        except Exception as e:
            self.logger.error(f"Failed to parse accident data: {e}")
            raise

    def process_deduplication(self, df: DataFrame) -> DataFrame:
        """Apply deduplication processing using UDF"""
        try:
            # Define UDF for deduplication
            def deduplicate_accident(row_dict):
                try:
                    result = self.deduplication_engine.process_event(row_dict)
                    return json.dumps(result)
                except Exception as e:
                    self.logger.error(f"Deduplication error: {e}")
                    return json.dumps(
                        {
                            **row_dict,
                            "is_duplicate": False,
                            "cluster_id": None,
                            "error": str(e),
                        }
                    )

            deduplicate_udf = udf(deduplicate_accident, StringType())

            # Apply deduplication
            dedup_df = (
                df.withColumn(
                    "dedup_result", deduplicate_udf(to_json(struct(*df.columns)))
                )
                .select(
                    from_json(col("dedup_result"), self.enriched_schema).alias(
                        "enriched"
                    )
                )
                .select("enriched.*")
            )

            self.logger.info("Applied deduplication processing")
            return dedup_df

        except Exception as e:
            self.logger.error(f"Failed to process deduplication: {e}")
            raise

    def process_person_identification(self, df: DataFrame) -> DataFrame:
        """Apply person identification processing"""
        try:
            # Define UDF for person identification
            def identify_persons(row_dict):
                try:
                    result = self.person_identifier.process_accident_for_identification(
                        row_dict
                    )
                    return json.dumps(result.get("identified_persons", []))
                except Exception as e:
                    self.logger.error(f"Person identification error: {e}")
                    return json.dumps([])

            identify_udf = udf(identify_persons, StringType())

            # Apply person identification
            identified_df = (
                df.withColumn(
                    "identified_persons_json",
                    identify_udf(to_json(struct(*df.columns))),
                )
                .withColumn(
                    "identified_persons",
                    from_json(col("identified_persons_json"), ArrayType(StringType())),
                )
                .drop("identified_persons_json")
            )

            self.logger.info("Applied person identification processing")
            return identified_df

        except Exception as e:
            self.logger.error(f"Failed to process person identification: {e}")
            raise

    def process_social_scraping(self, df: DataFrame) -> DataFrame:
        """Apply social media scraping processing"""
        try:
            # Define UDF for social scraping
            def scrape_social_profiles(row_dict):
                try:
                    posts = self.instagram_scraper.scrape_accident_location(row_dict)
                    profiles = self.instagram_scraper.extract_social_profiles(posts)
                    return json.dumps(profiles)
                except Exception as e:
                    self.logger.error(f"Social scraping error: {e}")
                    return json.dumps([])

            scrape_udf = udf(scrape_social_profiles, StringType())

            # Apply social scraping (only for non-duplicates)
            social_df = (
                df.withColumn(
                    "social_profiles_json",
                    when(
                        col("is_duplicate") is False,
                        scrape_udf(to_json(struct(*df.columns))),
                    ).otherwise(lit("[]")),
                )
                .withColumn(
                    "social_profiles",
                    from_json(col("social_profiles_json"), ArrayType(StringType())),
                )
                .drop("social_profiles_json")
            )

            self.logger.info("Applied social scraping processing")
            return social_df

        except Exception as e:
            self.logger.error(f"Failed to process social scraping: {e}")
            raise

    def add_processing_metadata(self, df: DataFrame) -> DataFrame:
        """Add processing metadata to DataFrame"""
        try:
            metadata_df = df.withColumn(
                "processing_timestamp", expr("unix_timestamp() * 1000")
            ).withColumn(
                "confidence_score",
                when(col("is_duplicate") is True, lit(0.0))
                .when(
                    col("identified_persons").isNotNull()
                    & (col("social_profiles").isNotNull()),
                    lit(0.9),
                )
                .when(col("identified_persons").isNotNull(), lit(0.7))
                .when(col("social_profiles").isNotNull(), lit(0.5))
                .otherwise(lit(0.3)),
            )

            self.logger.info("Added processing metadata")
            return metadata_df

        except Exception as e:
            self.logger.error(f"Failed to add processing metadata: {e}")
            raise

    def write_to_kafka(self, df: DataFrame, output_topic: str) -> StreamingQuery:
        """Write processed data back to Kafka"""
        try:
            query = (
                df.select(
                    col("accident_id").alias("key"),
                    to_json(struct(*df.columns)).alias("value"),
                )
                .writeStream.format("kafka")
                .option("kafka.bootstrap.servers", self.config.kafka_bootstrap_servers)
                .option("topic", output_topic)
                .option("checkpointLocation", f"./checkpoints/{output_topic}")
                .outputMode("append")
                .trigger(
                    processingTime=f"{self.config.micro_batch_duration_seconds} seconds"
                )
                .start()
            )

            self.logger.info(f"Started writing to Kafka topic: {output_topic}")
            return query

        except Exception as e:
            self.logger.error(f"Failed to write to Kafka: {e}")
            raise

    def write_to_console(self, df: DataFrame, query_name: str) -> StreamingQuery:
        """Write data to console for debugging"""
        try:
            query = (
                df.writeStream.format("console")
                .option("truncate", False)
                .option("numRows", 10)
                .outputMode("append")
                .queryName(query_name)
                .trigger(
                    processingTime=f"{self.config.micro_batch_duration_seconds} seconds"
                )
                .start()
            )

            self.logger.info(f"Started console output: {query_name}")
            return query

        except Exception as e:
            self.logger.error(f"Failed to write to console: {e}")
            raise

    def create_windowed_aggregation(self, df: DataFrame) -> DataFrame:
        """Create windowed aggregations for analytics"""
        try:
            # Create 5-minute windows for accident aggregation
            windowed_df = (
                df.withWatermark("kafka_timestamp", "10 minutes")
                .groupBy(
                    window(
                        col("kafka_timestamp"),
                        f"{self.config.window_duration_minutes} minutes",
                    ),
                    col("source"),
                )
                .agg(
                    count("*").alias("total_accidents"),
                    count(when(col("is_duplicate") is False, 1)).alias(
                        "unique_accidents"
                    ),
                    count(when(col("is_duplicate") is True, 1)).alias(
                        "duplicate_accidents"
                    ),
                    collect_list("accident_id").alias("accident_ids"),
                )
                .select(
                    col("window.start").alias("window_start"),
                    col("window.end").alias("window_end"),
                    col("source"),
                    col("total_accidents"),
                    col("unique_accidents"),
                    col("duplicate_accidents"),
                    col("accident_ids"),
                )
            )

            self.logger.info("Created windowed aggregation")
            return windowed_df

        except Exception as e:
            self.logger.error(f"Failed to create windowed aggregation: {e}")
            raise

    def run_processing_pipeline(self):
        """Run the complete accident processing pipeline"""
        try:
            self.logger.info("Starting accident processing pipeline")

            # Create input stream from Kafka
            raw_stream = self.create_kafka_stream(self.config.kafka_topic_accidents_raw)

            # Parse accident data
            parsed_stream = self.parse_accident_data(raw_stream)

            # Apply deduplication
            dedup_stream = self.process_deduplication(parsed_stream)

            # Apply person identification
            identified_stream = self.process_person_identification(dedup_stream)

            # Apply social scraping
            social_stream = self.process_social_scraping(identified_stream)

            # Add processing metadata
            final_stream = self.add_processing_metadata(social_stream)

            # Write to output Kafka topic
            output_query = self.write_to_kafka(
                final_stream, self.config.kafka_topic_accidents_processed
            )

            # Create windowed aggregations
            # Write aggregations to console (could be another Kafka topic)
            # Optional: Write raw processed data to console for debugging
            if self.config.debug:
                debug_query = self.write_to_console(final_stream, "processed_accidents")
                debug_query.awaitTermination()

            # Wait for queries to complete
            self.logger.info(
                "Pipeline started successfully, waiting for termination..."
            )
            output_query.awaitTermination()

        except Exception as e:
            self.logger.error(f"Error in processing pipeline: {e}")
            raise
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, "deduplication_engine"):
                self.deduplication_engine = None

            if hasattr(self, "person_identifier"):
                self.person_identifier.close()

            if hasattr(self, "instagram_scraper"):
                self.instagram_scraper.close()

            if hasattr(self, "spark"):
                self.spark.stop()

            self.logger.info("Cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    from ..utils.config import load_config

    # Load configuration
    config = load_config()

    # Create and run processor
    processor = SparkAccidentProcessor(config)

    try:
        processor.run_processing_pipeline()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"Pipeline error: {e}")
    finally:
        processor.cleanup()
