# DSA3101 Social Media Bias Detection

## Project Overview

This project is a **social media bias detection platform** that combines a FastAPI backend, a Streamlit frontend dashboard, and a MySQL database. The system imports both labelled and unlabelled datasets, detects bias in posts, and provides a dashboard for visualization and analysis.

**Key Features:**

* Detect bias in social media posts (`left`, `right`, `neutral`) using a pre-trained model.
* Store user activity and post data in MySQL.
* Dashboard visualization with Streamlit.
* Fully containerized using Docker and Docker Compose for easy deployment.

---

## Project Structure

```
dsa3101-2510-social_media-02/
│
├── backend/
│   ├── api/                  # FastAPI backend
│   │   ├── Dockerfile
│   │   ├── combined_api.py
│   │   ├── requirements.txt
│   │   └── ...
│   │
│   ├── database/             # MySQL database & CSV import
│   │   ├── Dockerfile
│   │   ├── create_tables.py
│   │   ├── data/             # CSV files
│   │   └── ...
│   │
│   └── labelling_model/      # Model code and notebooks
│
└── frontend/
    ├── Dockerfile
    ├── dashboarddemo.py      # Streamlit frontend
    ├── requirements.txt
    └── chrome_ex_t/          # Chrome extension (optional)
```

---

## Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop)
* [Docker Compose](https://docs.docker.com/compose/)

> Make sure Docker is running before using Docker Compose.

---

## Setup and Run

1. **Clone the repository**

```bash
git clone <repository_url>
cd dsa3101-2510-social_media-02
```

2. **Build and start all services**

```bash
docker-compose up --build
```

3. **Access services**

* Frontend Streamlit dashboard: [http://localhost:8501](http://localhost:8501)
* Backend API (FastAPI): [http://localhost:8000](http://localhost:8000)
* MySQL Database: `localhost:3306` (user: `kevin`, password: `kevin123`, database: `socialmedia`)

4. **Seed Database**

* The database is automatically seeded with CSV data using `create_tables.py` via the `db-seeder` service.

---

## Docker Services

| Service     | Description                                                      | Ports |
| ----------- | ---------------------------------------------------------------- | ----- |
| `database`  | MySQL server storing posts and user activity                     | 3306  |
| `db-seeder` | One-time service that runs `create_tables.py` to import CSV data | -     |
| `api`       | FastAPI backend exposing endpoints                               | 8000  |
| `frontend`  | Streamlit dashboard visualizing data                             | 8501  |

> Services are connected via a Docker network, so the backend can access the database by hostname `database`.

---

## Environment Variables

Set in `docker-compose.yml` or `.env` files:

```env
# Database
DB_HOST=database
DB_PORT=3306
DB_USER=kevin
DB_PASSWORD=kevin123
DB_NAME=socialmedia

# Backend API
API_HOST=0.0.0.0
API_PORT=8000

# Frontend (Streamlit)
FRONTEND_PORT=8501
```

---

## CSV Data

* `backend/database/data/unlabelled_data_clean.csv` → imported into `redditposts` table
* `backend/database/data/labelled_data_part1-10.csv` → combined into `newsarticles` table

---

## Usage

* Access Streamlit dashboard at `localhost:8501` to view posts and bias analysis.
* Use FastAPI endpoints at `localhost:8000` for programmatic access.
* Manage and query the database using SQL Workbench or other MySQL clients.

---

## Notes

* The database seeder (`db-seeder`) runs **once** at startup. If you need to reload CSVs, remove the database volume:

```bash
docker-compose down -v
docker-compose up --build
```

* All containers share the `socialmedia-net` network for internal communication.

---

## Troubleshooting

* **Docker cannot connect:** Ensure Docker Desktop is running.
* **Database connection fails:** Check credentials and network in `docker-compose.yml`.
* **Streamlit not loading:** Ensure port 8501 is free.

---
