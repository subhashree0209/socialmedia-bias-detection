# DSA3101 Group Project - Database Setup

A FastAPI application containerized with Docker that manages Reddit posts, news articles, and user activity data with MySQL as the backend database.

## Overview

This application provides a REST API built with FastAPI and uses MySQL for data persistence. It includes automated database initialization and data loading from CSV files.

## Features

- **FastAPI Backend**: High-performance REST API framework
- **MySQL Integration**: Robust relational database storage
- **Automated Data Loading**: Imports Reddit posts and news articles from CSV files
- **User Activity Tracking**: Monitors user interactions and recommendations
- **Containerized Deployment**: Easy deployment with Docker

## Prerequisites

- Docker
- Docker Compose (if using multi-container setup)
- CSV data files in the `data/` directory

## Directory Structure

```
.
├── Dockerfile
├── requirements.txt
├── create_tables.py  # Contains both DB initialization and FastAPI app
├── .gitignore
├── data/
│   ├── unlabelled_data_clean.csv
│   ├── labelled_data_part1.csv
│   ├── labelled_data_part2.csv
│   └── ... (labelled_data_part3-10.csv)
└── README.md
```

## Environment Variables

Configure the following environment variables for database connection:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL database host | `database` |
| `DB_USER` | Database username | `root` |
| `DB_PASSWORD` | Database password | `root` |
| `DB_NAME` | Database name | `mydatabase` |
| `DB_PORT` | Database port | `3306` |

## Database Schema

### Tables

#### `redditposts`
Stores unlabelled Reddit post data from `unlabelled_data_clean.csv`.

#### `newsarticles`
Stores labelled news article data from `labelled_data_part1.csv` through `labelled_data_part10.csv`.

#### `user_activity`
Tracks user interactions and recommendation triggers.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT (Primary Key) | Auto-incrementing identifier |
| `user_id` | VARCHAR(255) | User identifier |
| `title` | VARCHAR(255) | Post/article title |
| `body` | TEXT | Content body |
| `bias_label` | VARCHAR(50) | Bias classification label |
| `subreddit` | VARCHAR(255) | Source subreddit |
| `threshold_reached` | BOOLEAN | Whether threshold was reached |
| `recommendation_triggered` | BOOLEAN | Whether recommendation was sent |
| `recommended_post_urls` | TEXT | URLs of recommended posts |
| `timestamp` | TIMESTAMP | Activity timestamp |

## Application Architecture

The `create_tables.py` file serves dual purposes:

1. **Database Initialization** (runs on startup):
   - Establishes connection to MySQL with retry logic (up to 10 attempts)
   - Loads `unlabelled_data_clean.csv` into `redditposts` table
   - Combines all `labelled_data_part*.csv` files into `newsarticles` table
   - Creates the `user_activity` table for tracking user interactions

2. **FastAPI Application**: Hosts the REST API endpoints for the application

## API Access

Once running, the FastAPI application is accessible at:

- **Base URL**: `http://localhost:8001`
- **API Documentation**: `http://localhost:8001/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8001/redoc` (ReDoc)

## Data Requirements

Ensure the following CSV files are present in the `data/` directory:

- `unlabelled_data_clean.csv` - Reddit posts without labels
- `labelled_data_part1.csv` through `labelled_data_part10.csv` - Labelled news articles

## Troubleshooting

### Database Connection Issues

If the application fails to connect to MySQL:

- Verify MySQL is running and accessible
- Check environment variables are correctly set
- Ensure the database specified in `DB_NAME` exists (mydatabase)
- Review logs: `docker logs socialmedia-api`

### Missing Data Files

If CSV files are not found, check:

- Files are in the `data/` directory
- File names match exactly (case-sensitive)
- Files are copied into the container during build

### Port Conflicts

If port 8001 is already in use:

```bash
docker run -d -p 8002:8001 ... # Use different host port
```