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

# --- Import labelled data into newsarticles ---
newsarticles_parts = [f"labelled_data_part{i}.csv" for i in range(1, 11)]
newsarticles_df_list = []

for file in newsarticles_parts:
    path = os.path.join(data_folder, file)
    if os.path.exists(path):
        print(f"📥 Reading {file} for newsarticles table")
        newsarticles_df_list.append(pd.read_csv(path))

# Concatenate all parts into one DataFrame
newsarticles_df = pd.concat(newsarticles_df_list, ignore_index=True)
newsarticles_df.to_sql("newsarticles", con=engine, if_exists="replace", index=False)
print(f"✅ Imported all labelled data into 'newsarticles' table!")

# --- Import unlabelled data into redditposts ---
unlabelled_file = os.path.join(data_folder, "unlabelled_data_clean.csv")
if os.path.exists(unlabelled_file):
    print(f"📥 Importing unlabelled_data_clean.csv → redditposts table")
    unlabelled_df = pd.read_csv(unlabelled_file)
    unlabelled_df.to_sql("redditposts", con=engine, if_exists="replace", index=False)
    print(f"✅ Imported unlabelled data into 'redditposts' table!")

print("🎉 All CSV files imported successfully!")