import os
import time
import pandas as pd
from sqlalchemy import create_engine

# Wait a bit for MySQL to be ready
time.sleep(10)

# Environment variables from docker-compose.yml
db_host = os.getenv("MYSQL_HOST", "db")
db_user = os.getenv("MYSQL_USER", "root")
db_password = os.getenv("MYSQL_PASSWORD", "root")
db_name = os.getenv("MYSQL_DATABASE", "mydatabase")

# Create SQLAlchemy connection
engine_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:3306/{db_name}"
engine = create_engine(engine_str)

data_folder = "data"

# Loop through CSV files
for file in os.listdir(data_folder):
    if file.endswith(".csv"):
        table_name = os.path.splitext(file)[0]
        path = os.path.join(data_folder, file)
        print(f"📥 Importing {file} → table '{table_name}'")

        df = pd.read_csv(path)
        df.to_sql(table_name, con=engine, if_exists="replace", index=False)

print("✅ All CSV files imported successfully!")