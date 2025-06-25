# Setup Guide - Real-Time Accident Detection System

## ✅ Setup Status: COMPLETED

The basic setup has been completed successfully! The main issues have been resolved:

### 🔧 Issues Fixed:

1. **Path Handling**: Fixed Windows path issues with spaces in directory names
2. **Pip Upgrade**: Changed from direct pip calls to `python -m pip` for better compatibility
3. **Dependencies**: Simplified requirements.txt to avoid compilation issues on Windows

### 📁 What Was Created:

- ✅ Virtual environment (`venv/`)
- ✅ Project directories (`logs/`, `data/`, `checkpoints/`)
- ✅ Environment file (`.env` from `.env.example`)
- ✅ Sample scripts (`scripts/create_kafka_topics.sh`, `run.py`)
- ✅ Core Python dependencies installed

## 🚀 Next Steps

### 1. Install Additional Dependencies (Optional)

The core system is working with minimal dependencies. Install additional packages as needed:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install specific packages you need:
pip install kafka-python==2.0.2
pip install pandas numpy
pip install redis pymongo
pip install instaloader twilio boto3

# For Spark (requires Java 11+):
pip install pyspark==3.5.0

# For web scraping:
pip install selenium
```

### 2. Install System Dependencies

#### Docker Desktop (Required for Kafka, Redis, etc.)
- Download from: https://www.docker.com/products/docker-desktop/
- Install and restart your computer
- Verify: `docker --version`

#### Java 11+ (Required for Spark)
- Download OpenJDK: https://adoptium.net/
- Add to PATH environment variable
- Verify: `java -version`

### 3. Configure Environment

Edit the `.env` file with your API keys:

```bash
# Waze API (if available)
WAZE_API_KEY=your_waze_api_key

# Social Media APIs
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Communication
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# AWS (for additional services)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

# Database connections
REDIS_URL=redis://localhost:6379
MONGO_URL=mongodb://localhost:27017
NEO4J_URI=bolt://localhost:7687
```

### 4. Start Services

```powershell
# Start Docker services
docker-compose up -d

# Wait for services to start (30 seconds)
# Then create Kafka topics
.\scripts\create_kafka_topics.sh

# Run the application
python run.py
# OR
python main.py
```

### 5. Verify Installation

```powershell
# Check if services are running
docker-compose ps

# Test the application
python -c "from src.utils.config import Config; print('Config loaded successfully!')"

# Run tests
python -m pytest tests/ -v
```

## 🔍 Troubleshooting

### Common Issues:

1. **Docker not found**:
   - Install Docker Desktop
   - Restart PowerShell after installation

2. **Java not found** (for Spark):
   - Install OpenJDK 11+
   - Add Java to PATH

3. **Package installation fails**:
   - Try installing packages one by one
   - Use `--no-cache-dir` flag: `pip install --no-cache-dir package_name`

4. **Permission errors**:
   - Run PowerShell as Administrator
   - Or use: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Package-Specific Issues:

- **pandas/numpy**: Use pre-compiled wheels: `pip install --only-binary=all pandas numpy`
- **psycopg2**: Use binary version: `pip install psycopg2-binary`
- **cryptography**: Update pip first: `python -m pip install --upgrade pip`

## 📊 System Architecture

The system consists of:

1. **Data Collection**: Waze API integration
2. **Stream Processing**: Kafka + Spark Streaming
3. **Person Identification**: Vehicle registration + social media
4. **Storage**: Redis (cache) + MongoDB (data) + Neo4j (relationships)
5. **Monitoring**: Custom metrics and alerting

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use strong passwords for all services
- Regularly rotate API keys
- Monitor access logs

## 📚 Additional Resources

- **Kafka**: https://kafka.apache.org/documentation/
- **Spark**: https://spark.apache.org/docs/latest/
- **Docker**: https://docs.docker.com/
- **FastAPI**: https://fastapi.tiangolo.com/

---

**Status**: ✅ Basic setup complete
**Next**: Install Docker Desktop and Java, then configure services
**Support**: Check logs in `logs/` directory for troubleshooting