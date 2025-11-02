import os
import time
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


# STEP 1: Read environment variables
db_host = os.getenv("DB_HOST", "database")
db_user = os.getenv("DB_USER", "root")        
db_password = os.getenv("DB_PASSWORD", "root") 
db_name = os.getenv("DB_NAME", "mydatabase") 
db_port = os.getenv("DB_PORT", "3306")

engine_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
print(f"🔗 Connecting to MySQL at {db_host}:{db_port}...")

# STEP 2: Wait until MySQL is ready
max_retries = 10
for i in range(max_retries):
    try:
        engine = create_engine(engine_str)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("MySQL connection established!")
        break
    except OperationalError as e:
        print(f"Waiting for MySQL... ({i+1}/{max_retries})")
        time.sleep(5)
else:
    raise RuntimeError("Could not connect to MySQL after multiple attempts.")


# STEP 3: Load data into MySQL tables
data_folder = "data"

# --- Unlabelled data → redditposts ---
unlabelled_file = os.path.join(data_folder, "unlabelled_data_clean.csv")
if os.path.exists(unlabelled_file):
    print(f"Importing {unlabelled_file} → table 'redditposts'")
    df_unlabelled = pd.read_csv(unlabelled_file)
    df_unlabelled.to_sql("redditposts", con=engine, if_exists="replace", index=False)
else:
    print("Unlabelled data file not found!")

# --- Labelled data → newsarticles ---
labelled_files = [f"labelled_data_part{i}.csv" for i in range(1, 11)]
newsarticles_df_list = []

for file in labelled_files:
    path = os.path.join(data_folder, file)
    if os.path.exists(path):
        print(f"Reading {file} for newsarticles table")
        df = pd.read_csv(path)
        newsarticles_df_list.append(df)

if newsarticles_df_list:
    all_labelled_df = pd.concat(newsarticles_df_list, ignore_index=True)
    print(f"Writing combined labelled data → table 'newsarticles'")
    all_labelled_df.to_sql("newsarticles", con=engine, if_exists="replace", index=False)
else:
    print("No labelled CSVs found!")


# STEP 4: Create user_activity table
print("Creating 'user_activity' table (if not exists)...")

create_user_activity_table_query = """
CREATE TABLE IF NOT EXISTS user_activity (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(255),
    title VARCHAR(255),
    body TEXT,
    bias_label VARCHAR(50),
    subreddit VARCHAR(255),
    threshold_reached BOOLEAN DEFAULT FALSE,
    recommendation_triggered BOOLEAN DEFAULT FALSE,
    recommended_post_urls TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

with engine.connect() as connection:
    connection.execute(text(create_user_activity_table_query))
    connection.commit()

print("'user_activity' table ready!")
print("All CSV files imported and tables created successfully!")
