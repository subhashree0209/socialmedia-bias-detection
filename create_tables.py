import os
import time
import pandas as pd
from sqlalchemy import create_engine, text

# Wait for MySQL to be ready
time.sleep(10)

# Environment variables from docker-compose.yml
db_host = os.getenv("MYSQL_HOST", "mysql_db")
db_user = os.getenv("MYSQL_USER", "root")
db_password = os.getenv("MYSQL_PASSWORD", "root")
db_name = os.getenv("MYSQL_DATABASE", "mydatabase")

# Create SQLAlchemy connection
engine_str = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:3306/{db_name}"
engine = create_engine(engine_str)

data_folder = "data"

# Import unlabelled data → redditposts
unlabelled_file = os.path.join(data_folder, "unlabelled_data_clean.csv")
if os.path.exists(unlabelled_file):
    print(f"📥 Importing {unlabelled_file} → table 'redditposts'")
    df_unlabelled = pd.read_csv(unlabelled_file)
    df_unlabelled.to_sql("redditposts", con=engine, if_exists="replace", index=False)

# Import labelled data → newsarticles
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

# CREATE user_activity table in mysql db (with "IF NOT EXISTS" to prevent errors)
print("Creating 'user_activity' table if it doesn't exist")
create_user_activity_table_query = """
CREATE TABLE IF NOT EXISTS user_activity (
    id INT PRIMARY KEY AUTO_INCREMENT,                -- unique ID for each user activity record (BACKEND - just create a row number) [CHANGED FROM user_activity_id to id]
    user_id VARCHAR(255),                             -- user identifier (FRONTEND)
    title VARCHAR(255),                               -- title of the post (FRONTEND)
    body TEXT,                                        -- body/content of the post (FRONTEND)
    bias_label VARCHAR(50),                           -- bias of the post ('left', 'right', 'neutral') (BACKEND - api/recommend endpoint)
    threshold_reached BOOLEAN DEFAULT FALSE,          -- flag indicating if the user has viewed 20 posts of the same bias (BACKEND - api/recommend endpoint)
    recommendation_triggered BOOLEAN DEFAULT FALSE,   -- flag indicating if a recommendation was triggered for this post (BACKEND - api/recommend endpoint)
    recommended_post_urls TEXT,                       -- store recommended post URLs (JSON or comma-separated list) (BACKEND - api/recommend endpoint)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- timestamp of the user activity (when the post was viewed) (BACKEND - create a timestamp)
);
"""
# execute the query to create the table (sqlalchemy engine)
with engine.connect() as connection:
    connection.execute(text(create_user_activity_table_query))
    connection.commit()

print("'user_activity' table created successfully!")

print("All CSV files imported successfully!")