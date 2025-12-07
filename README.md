# EchoBreak: Social Media Bias Detection for Reddit

A comprehensive platform for detecting political bias in social media content and providing counter-recommendation to promote balanced information consumption. The system analyzes Reddit posts, tracks user bias patterns, and recommends diverse perspectives when bias thresholds are reached.

## Overview

This platform combines machine learning-based bias detection with intelligent recommendation algorithms to help users consume more balanced social media content. It tracks user engagement patterns, detects political bias (left, right, or neutral), and provides counter-recommendations when users show sustained bias in their content consumption.

### Key Features

- **Bias Detection**: RoBERTa-based ML model classifies content as left-leaning, right-leaning, or neutral
- **User Activity Tracking**: Monitors user engagement patterns across subreddits
- **Smart Recommendations**: Provides counter-recommendations (2 neutral + 2 opposite-bias posts) when bias threshold is reached
- **Analytics Dashboard**: Real-time visualization of user engagement, political spectrum, screentime analysis, and top subreddits
- **Reddit Integration**: Searches and analyzes live Reddit content using PRAW

## Architecture

```
root/
├── backend/
│   ├── api/                          # FastAPI REST API service
│   │   ├── combined_api.py           # Main API with bias detection & recommendations
│   │   ├── Dockerfile                # API container configuration
│   │   ├── requirements.txt          # API dependencies
│   │   ├── .dockerignore
│   │   ├── .gitignore
│   │   ├── README.me
│   │   └── .env                      # Environment variables (not in Git)
│   │
│   ├── database/                     # Database initialization service
│   │   ├── create_tables.py          # DB setup and data loading
│   │   ├── Dockerfile                # Database service container
│   │   ├── requirements.txt          # Database dependencies
│   │   ├── .gitignore
│   │   ├── README.me
│   │   └── data/                     # CSV data files
│   │       ├── unlabelled_data_clean.csv
│   │       └── labelled_data_part[1-10].csv
│   │
│   └── labelling_model/              # ML model development
│       ├── bias_model.py             # Model training script
│       └── bias_model.ipynb          # Model development notebook
│
├── frontend/                         # Streamlit analytics dashboard
│   ├── dashboarddemo.py              # Main dashboard application
│   ├── Dockerfile                    # Frontend container configuration
│   ├── .env
│   ├── .gitignore
│   ├── chrome_ex_t
│   ├── README.me
│   └── requirements.txt              # Frontend dependencies
│
├── docker-compose.yml                # Multi-container orchestration
├── .gitignore
└── README.me
```

## System Components

### 1. MySQL Database (`mysql_db`)
- **Image**: MySQL 8.0
- **Port**: 3306
- **Purpose**: Stores Reddit posts, news articles, and user activity data

**Tables**:
- `redditposts` - Unlabelled Reddit post data
- `newsarticles` - Labelled news articles with bias classifications
- `user_activity` - User engagement tracking and recommendations

### 2. Database Seeder (`socialmedia-db-seeder`)
- **Purpose**: Initializes database tables and loads CSV data
- **Run Mode**: Runs once on startup (`restart: "no"`)
- **Command**: `python create_tables.py`
- **Data Loaded**:
  - Unlabelled Reddit posts → `redditposts` table
  - 10 labelled news article files → `newsarticles` table
  - Creates `user_activity` table structure
- **Note**: Waits for MySQL healthcheck to pass before running

### 3. API Service (`socialmedia-api`)
- **Port**: 8000
- **Framework**: FastAPI with Uvicorn
- **ML Model**: RoBERTa for sequence classification (hosted on AWS S3)
- **Keyword Extraction**: KeyBERT for content analysis
- **Reddit Integration**: PRAW for live Reddit search

**Endpoints**:
- `POST /classify` - Classify single text for bias
- `POST /classify_batch` - Classify multiple texts for bias
- `POST /api/related` - Get related posts and log to database
- `POST /api/recommend` - Track bias and trigger recommendations when threshold reached
- `GET /health` - Health check endpoint

**Key Features**:
- Downloads ML model from AWS S3 on startup (with volume caching)
- Tracks user bias counts (threshold: 5 posts)
- Provides 2 neutral + 2 opposite-bias recommendations
- Logs all activity to MySQL database

### 4. Frontend Dashboard (`socialmedia-frontend`)
- **Port**: 8501
- **Framework**: Streamlit
- **Purpose**: Real-time analytics and visualization

**Dashboard Features**:
- **Political Spectrum Analysis**: Pie chart showing distribution of left/right/neutral posts
- **Screentime Analysis**: Donut chart breaking down time in "Skeptical Mode" vs "Vibes Mode"
- **Top Subreddits**: Horizontal bar chart of most engaged subreddits
- **Live Data**: Connects to MySQL for real-time user activity data

## Prerequisites

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **AWS Account** (for S3 model storage)
- **Reddit API Credentials** ([Get them here](https://www.reddit.com/prefs/apps))

## Environment Variables

### API Service (`.env` in `backend/api/`)

Create a `.env` file in `backend/api/` with the following:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://root:root@database:3306/mydatabase

# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_SECRET_ID=your_reddit_secret_id

# AWS S3 Configuration (for ML model storage)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_aws_region

# Model Configuration
S3_BUCKET_NAME=dsa3101-socialmedia02-model
MODEL_FILE=bias_model.pkl
```

### Database Seeder Service (environment variables in docker-compose.yml)

The database seeder uses these connection variables:
- `DB_HOST=database`
- `DB_PORT=3306`
- `DB_USER=root`
- `DB_PASSWORD=root`
- `DB_NAME=mydatabase`

### Frontend Service (environment variables in docker-compose.yml)

The frontend automatically uses these database connection variables:
- `DB_HOST=database`
- `DB_PORT=3306`
- `DB_USER=root`
- `DB_PASSWORD=root`
- `DB_NAME=mydatabase`

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <project-directory>
```

### 2. Set Up Environment Variables

Create `.env` file in `backend/api/`:

```bash
cd backend/api
# Create new .env and add your credentials
nano .env
```

### 3. Start All Services

From the project root directory:

```bash
docker-compose up -d
```

This will:
1. Start MySQL database
2. Wait for database health check
3. Run database seeder (loads CSV data)
4. Start API service (downloads ML model from S3)
5. Start frontend dashboard

### 4. Verify Services

Check all containers are running:

```bash
docker-compose ps
```

You should see:
- `mysql_db` - running (healthy)
- `socialmedia-db-seeder` - exited (completed successfully)
- `socialmedia-api` - running
- `socialmedia-frontend` - running

### 5. Access the Application

- **Frontend Dashboard**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## Usage

### Using the Dashboard

1. Navigate to http://localhost:8501
2. View real-time analytics:
   - Political spectrum distribution
   - Screentime breakdown by mode
   - Top subreddit engagement

The dashboard automatically refreshes data from the database.

## Development

### Rebuilding Services

After making code changes:

```bash
# Rebuild specific service
docker-compose build api
docker-compose up -d api

# Rebuild all services
docker-compose build
docker-compose up -d

# Force rebuild (no cache)
docker-compose build --no-cache
docker-compose up -d
```

### View Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs frontend
docker-compose logs database

# Follow logs in real-time
docker-compose logs -f api
```

### Access Database

```bash
# MySQL CLI access
docker exec -it mysql_db mysql -u root -proot mydatabase

# Check tables
docker exec -it mysql_db mysql -u root -proot mydatabase -e "SHOW TABLES;"

# View user activity
docker exec -it mysql_db mysql -u root -proot mydatabase -e "SELECT * FROM user_activity ORDER BY timestamp DESC LIMIT 10;"
```

### Local Development (Without Docker)

#### API Service

```bash
cd backend/api
pip install -r requirements.txt

# Set environment variables or create .env file
export DATABASE_URL="mysql+pymysql://root:root@localhost:3306/mydatabase"
export REDDIT_CLIENT_ID="your_id"
# ... other variables

# Run API
uvicorn combined_api:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
pip install -r requirements.txt

# Set environment variables
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=root
export DB_NAME=mydatabase

# Run dashboard
streamlit run dashboarddemo.py --server.port=8501
```

## Data Requirements

### CSV Files for Database Seeding

Place these files in `backend/database/data/`:

1. **unlabelled_data_clean.csv** - Reddit posts without labels
   - Loaded into `redditposts` table

2. **labelled_data_part1.csv through labelled_data_part10.csv** - News articles with bias labels
   - Combined and loaded into `newsarticles` table

### ML Model File

- **Location**: AWS S3 bucket
- **File**: `bias_model.pkl`
- **Contents**: Pickled dictionary with:
  - `model`: RoBERTa sequence classification model
  - `tokenizer`: RoBERTa tokenizer
- **Caching**: Downloaded once and cached in Docker volume `model_cache`

## Troubleshooting

### Services Won't Start

**Check logs**:
```bash
docker-compose logs
```

**Common issues**:
- Missing `.env` file in `backend/api/`
- Invalid AWS credentials
- Port conflicts (3306, 8000, 8501 already in use)

### Database Connection Failed

**Check MySQL is running**:
```bash
docker-compose ps database
```

**Verify database health**:
```bash
docker exec mysql_db mysqladmin ping -h localhost -u root -proot
```

**Check if database exists**:
```bash
docker exec -it mysql_db mysql -u root -proot -e "SHOW DATABASES;"
```

### API Model Loading Issues

**Check S3 credentials**:
```bash
docker-compose logs api | grep "S3\|AWS\|Model"
```

**Verify model cache**:
```bash
docker exec socialmedia-api ls -la /app/bias_model.pkl
```

**Force model re-download**:
```bash
# Remove cached model
docker exec socialmedia-api rm /app/bias_model.pkl
# Restart API
docker-compose restart api
```

### Frontend Not Showing Data

**Check database connection**:
```bash
docker-compose logs frontend | grep "Database"
```

**Verify data exists**:
```bash
docker exec -it mysql_db mysql -u root -proot mydatabase -e "
  SELECT COUNT(*) as count FROM user_activity;
"
```

**Clear Streamlit cache**:
- Refresh browser (Ctrl+Shift+R)
- Or press 'C' in Streamlit UI to clear cache

### Reddit API Errors

**Check credentials**:
```bash
docker-compose logs api | grep "Reddit\|PRAW"
```

**Test Reddit connection**:
```bash
curl http://localhost:8000/health
```

Look for `"reddit_connected": true` in response.

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Use port 8001 on host instead
  
  frontend:
    ports:
      - "8502:8501"  # Use port 8502 on host instead
```

### Database Seeder Failed

**Check seeder logs**:
```bash
docker-compose logs db-seeder
```

**Common issues**:
- Missing CSV files in `backend/database/data/`
- Database not ready (healthcheck failed)
- File permission issues

**Manually re-run seeder**:
```bash
docker-compose up db-seeder
```

## Testing

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database connection
docker exec mysql_db mysqladmin ping -h localhost -u root -proot

# Frontend accessibility
curl -I http://localhost:8501
```

### Verify Data Loading

```bash
# Check table counts
docker exec -it mysql_db mysql -u root -proot mydatabase -e "
  SELECT 
    (SELECT COUNT(*) FROM redditposts) as reddit_posts,
    (SELECT COUNT(*) FROM newsarticles) as news_articles,
    (SELECT COUNT(*) FROM user_activity) as user_activities;
"
```

### Test API Endpoints

```bash
# Test classification
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test post about politics"}'

# Test health endpoint
curl http://localhost:8000/health
```

## Stopping Services

### Stop all services:
```bash
docker-compose down
```

### Stop and remove volumes (⚠️ deletes all data):
```bash
docker-compose down -v
```

### Stop specific service:
```bash
docker-compose stop api
```

## Production Considerations

- **Security**:
  - Use Docker secrets for sensitive credentials
  - Enable HTTPS/TLS for API and frontend
  - Restrict database access to backend network only
  - Rotate API keys regularly

- **Performance**:
  - Configure connection pooling for database
  - Implement API rate limiting
  - Use Redis for caching frequently accessed data
  - Scale API service horizontally with load balancer

- **Monitoring**:
  - Set up logging aggregation (ELK stack, CloudWatch)
  - Configure health check endpoints for orchestration
  - Monitor model inference latency
  - Track database query performance

- **Backup**:
  - Automated MySQL backups
  - S3 versioning for ML model
  - Volume snapshots for persistent data

## Architecture Decisions

### Why Separate DB Seeder?

The database seeder runs once on startup to populate initial data, then exits. This prevents:
- Duplicate data loading on API restarts
- Resource overhead from keeping seeder running
- Cleaner separation of concerns

### Why Model Caching?

The ML model (~500MB) is downloaded from S3 only once and cached in a Docker volume. This:
- Speeds up API container restarts
- Reduces S3 egress costs
- Improves deployment reliability

### Why FastAPI?

FastAPI provides:
- Automatic OpenAPI documentation
- Type validation with Pydantic
- High performance (async support)
- Easy integration with ML models

## Contributing

1. Create a feature branch
2. Make changes in appropriate service directory
3. Test locally with Docker Compose
4. Update relevant README files
5. Submit pull request

## Support

For issues or questions:
- Check troubleshooting section above
- Review logs: `docker-compose logs <service-name>`
- Open an issue on GitHub
