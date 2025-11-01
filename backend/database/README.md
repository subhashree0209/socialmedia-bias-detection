# DSA3101 Group Project - Database Setup

This repository contains the scripts and Docker configuration to set up a MySQL database and import CSV files for the DSA3101 Group Project.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository_url>
cd create_database

# Build and start everything with one command
docker-compose up --build

# Access the database
docker exec -it mysql_db mysql -u root -proot
```

---

## 📋 Table of Contents
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Database Configuration](#database-configuration)
- [Data Format Requirements](#data-format-requirements)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Authors](#authors)

---

## 📁 Project Structure

```
database/
├── data/
│   ├── unlabelled_data_clean.csv
│   ├── labelled_data_part1.csv
│   ├── labelled_data_part2.csv
│   ├── ...
│   └── labelled_data_part10.csv
├── Dockerfile
├── docker-compose.yml
├── import_csvs.py
├── requirements.txt
└── README.md
```

### File Descriptions

| File/Folder | Description |
|-------------|-------------|
| `data/` | Contains CSV files to be imported into the MySQL database |
| `Dockerfile` | Defines the Python environment for the CSV importer |
| `docker-compose.yml` | Orchestrates the MySQL database and importer containers |
| `import_csvs.py` | Python script that imports CSV files into the database |
| `requirements.txt` | Python dependencies (pandas, pymysql, sqlalchemy, cryptography) |

---

## 💻 Requirements

- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **Internet connection** (to download Python packages and Docker images)
- **Minimum 2GB free disk space**

### Check if Docker is installed:

```bash
docker --version
docker-compose --version
```

---

## 🔧 Setup Instructions

### Step 1: Clone the Repository

```bash
git clone <repository_url>
cd create_database
```

### Step 2: Prepare Your CSV Files

Ensure your CSV files are in the `data/` directory:
- `unlabelled_data_clean.csv` → will be imported into redditposts
- `labelled_data_part1.csv` → `labelled_data_part10.csv` → will be combined into newsarticles

### Step 3: Build and Start the Containers

```bash
docker-compose up --build
```

This command will:
1. ✅ Pull the MySQL 8.0 Docker image
2. ✅ Build the Python importer container
3. ✅ Start the MySQL database
4. ✅ Wait for MySQL to be ready
5. ✅ Import CSV files into the database
6. ✅ Exit the importer container automatically

### Step 4: Verify Setup

Check that the MySQL container is running:

```bash
docker ps
```

You should see a container named `mysql_db` in the list.

---

## 🎯 Usage

### Accessing the MySQL Database

#### Option 1: Using Docker Exec

```bash
docker exec -it mysql_db mysql -u root -prootpassword
```

#### Option 2: Using MySQL Client (if installed locally)

```bash
mysql -h 127.0.0.1 -P 3306 -u root -prootpassword
```

### Running SQL Queries

Once connected to MySQL:

```sql
-- Show all databases
SHOW DATABASES;

-- Use your database
USE mydatabase;

-- Show all tables
SHOW TABLES;

-- View labelled data
SELECT * FROM newsarticles LIMIT 10;

-- View unlabelled data
SELECT * FROM redditposts LIMIT 10;

-- Check table structure
DESCRIBE newsarticles;
DESCRIBE redditposts;

-- Count records
SELECT COUNT(*) FROM newsarticles;
SELECT COUNT(*) FROM redditposts;
```

### Re-importing CSV Files

If you update the CSV files and need to re-import:

```bash
# Stop the current containers
docker-compose down

# Re-run the importer
docker-compose up
```

Or, to only re-run the importer without rebuilding:

```bash
docker-compose run --rm csv_importer
```

---

## ⚙️ Database Configuration

### Connection Details

| Parameter | Value |
|-----------|-------|
| **Host** | `localhost` or `127.0.0.1` |
| **Port** | `3306` |
| **Database** | `dsa3101_db` |
| **Username** | `root` |
| **Password** | `root` |

### Tables Created

1. **newsarticles**
   - Contains the cleaned labelled dataset
   - Table structure matches CSV columns
   
2. **redditposts**
   - Contains the cleaned unlabelled dataset
   - Table structure matches CSV columns

### Modifying Configuration

To change database credentials, edit `docker-compose.yml`:

```yaml
environment:
  MYSQL_ROOT_PASSWORD: your_new_password
  MYSQL_DATABASE: your_database_name
```

**Important:** If you change credentials, also update them in `import_csvs.py`.

---

## 📊 Data Format Requirements

### CSV File Requirements

- **File Format:** UTF-8 encoded CSV
- **Headers:** First row must contain column names
- **Delimiter:** Comma (`,`)
- **Missing Values:** Empty cells are imported as NULL

### Adding New CSV Files

1. Place your CSV file in the `data/` directory
2. Update `import_csvs.py` to include your new file:

```python
csv_files = {
    'newsarticles': ['data/labelled_data_part1.csv', 'data/labelled_data_part2.csv'],
    'redditposts': 'data/unlabelled_data_clean.csv',
    'your_new_table': 'data/your_new_file.csv'  # Add this line
}
```

3. Re-run the importer:

```bash
docker-compose run --rm csv_importer
```

---

## 🔍 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Port 3306 Already in Use

**Error Message:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:3306: bind: address already in use
```

**Solution:**
```bash
# Option 1: Stop local MySQL service
sudo systemctl stop mysql  # Linux
brew services stop mysql   # macOS

# Option 2: Change the port in docker-compose.yml
ports:
  - "3307:3306"  # Use port 3307 instead
```

#### Issue 2: Cryptography Package Error

**Error Message:**
```
RuntimeError: 'cryptography' package is required
```

**Solution:**
Already included in `requirements.txt`. If the error persists, rebuild:
```bash
docker-compose down
docker-compose up --build
```

#### Issue 3: MySQL Container Not Starting

**Solution:**
```bash
# Check container logs
docker logs mysql_db

# Remove old volumes and restart
docker-compose down -v
docker-compose up --build
```

#### Issue 4: CSV Import Fails

**Error Message:**
```
FileNotFoundError: [Errno 2] No such file or directory
```

**Solution:**
- Verify CSV files exist in the `data/` directory
- Check file names match exactly (case-sensitive)
- Ensure CSV files are not corrupted

#### Issue 5: Docker Compose Version Warning

**Warning Message:**
```
version is obsolete
```

**Solution:**
This warning can be safely ignored. The configuration works with both old and new Docker Compose versions.

### Getting Help

If you encounter other issues:
1. Check Docker logs: `docker logs mysql_db` and `docker logs csv_importer`
2. Verify Docker is running: `docker ps`
3. Check disk space: `df -h`

---

## 🧹 Cleanup

### Stop Containers (Keep Data)

```bash
docker-compose down
```

### Stop Containers and Remove Data

```bash
# WARNING: This will delete all data in the database
docker-compose down -v
```

### Remove Docker Images

```bash
# List images
docker images

# Remove the importer image
docker rmi create_database-csv_importer

# Remove MySQL image (optional)
docker rmi mysql:8.0
```

### Complete Cleanup

```bash
# Stop and remove everything
docker-compose down -v
docker system prune -a
```

---

## 👥 Authors

- **Kevin Zhu Chun Yin**
- [Add other group members here]

---

## 📝 License

[Specify your license here, e.g., MIT License]

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/YourFeature`
3. Commit your changes: `git commit -m 'Add YourFeature'`
4. Push to the branch: `git push origin feature/YourFeature`
5. Open a Pull Request

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

**Last Updated:** October 2025