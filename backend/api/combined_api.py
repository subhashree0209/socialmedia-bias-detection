from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
from keybert import KeyBERT
from collections import defaultdict
import praw
import os
from dotenv import load_dotenv
import uvicorn
from sqlalchemy import create_engine, Table, MetaData, insert, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime
import json
import requests
import pickle
import boto3
from boto3.s3.transfer import TransferConfig

# Load environment variables FIRST
load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@database:3306/mydatabase")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the metadata
metadata = MetaData()

# Define table structure (this should match your database schema)
user_activity = Table(
    'user_activity',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(255)),
    Column('title', String(255)),
    Column('body', Text),
    Column('bias_label', String(50)),
    Column('subreddit', String(255)),
    Column('threshold_reached', Boolean, default=False),
    Column('recommendation_triggered', Boolean, default=False),
    Column('recommended_post_urls', Text),
    Column('timestamp', DateTime, default=func.now()),
    extend_existing=True
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Get the AWS credentials from environment
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID") 
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION")

# Set credentials for boto3 session
boto3.setup_default_session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

# S3 CLIENT SETUP
s3 = boto3.client('s3')

# S3 Configuration
bucket_name = 'dsa3101-socialmedia02-model'
model_file = 'bias_model.pkl'
local_path = './bias_model.pkl'


def load_model_from_s3():
    """Download model from S3 only if not cached in volume"""
    print(f"Checking if model exists at {local_path}...")
    # Check if model already exists in the persistent volume
    if os.path.exists(local_path):
        print("[CACHE HIT] Model found in cache, skipping download")
        return True
    
    try:
        print("[DOWNLOADING] Model not in cache, downloading from S3...")
        config = TransferConfig(
            multipart_threshold=1024 * 1024 * 5,
            max_concurrency=50,
            multipart_chunksize=1024 * 1024 * 5,
            use_threads=True,
            max_bandwidth=None
        )
        
        s3.download_file(bucket_name, model_file, local_path, Config=config)
        print("[COMPLETE] Model downloaded!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    
# Initialize global variables for model and tokenizer
model = None
tokenizer = None
label_mapping = {0: "left", 1: "neutral", 2: "right"}

# --- FASTAPI APP ---
app = FastAPI(title="Bias Detection and Recommendation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup event AFTER app is created
@app.on_event("startup")
async def startup_event():
    """Initialize database connection and load model from S3"""
    global model, tokenizer
    
    try:
        # Database setup
        metadata.reflect(bind=engine)
        print("Database tables loaded successfully")
        
        metadata.create_all(bind=engine)
        print("Tables verified/created")
        
        # Load model from S3
        model_loaded = load_model_from_s3() 
        
        if model_loaded:
            print("Loading model into memory...")
            with open(local_path, 'rb') as f:
                saved_data = pickle.load(f)
                model = saved_data['model']
                tokenizer = saved_data['tokenizer']
            
            model.eval()
            print("Model and tokenizer ready!")
        else:
            print("Failed to load model from S3!")
            raise Exception("Model loading failed - cannot start API")
        
    except Exception as e:
        print(f"Startup error: {e}")
        raise

# --- KEYWORD MODEL ---
kw_model = KeyBERT()

# --- USER BIAS TRACKER ---
user_bias_data = defaultdict(lambda: {"left": 0, "right": 0})
BIAS_THRESHOLD = 20

# --- REDDIT API ---
client_id = os.getenv("REDDIT_CLIENT_ID")
secret_id = os.getenv("REDDIT_SECRET_ID")
user_agent = "counter_recommendation_system"

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=secret_id,
    user_agent=user_agent
)

# --- PYDANTIC MODELS ---
class TextInput(BaseModel):
    text: str

class BatchInput(BaseModel):
    texts: list[str]

class RelatedRequest(BaseModel):
    user_id: str
    title: str = ""
    post: str = ""
    label: str
    subreddit: str

class RecommendRequest(BaseModel):
    user_id: str
    title: str = ""
    post: str = ""
    label: str
    subreddit: str = ""

# --- CLASSIFICATION FUNCTIONS ---
def classifier(text):
    """Classify text as left, right, or neutral"""
    if not text or not text.strip():
        return "neutral"

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        prediction = torch.argmax(logits, dim=1).item()

    # labels: 0=left, 1=neutral, 2=right
    if prediction == 0:
        return "left"
    elif prediction == 2:
        return "right"
    else:
        return "neutral"

@app.post("/classify")
def classify_single(input_data: TextInput):
    """Classify single text for bias"""
    text = input_data.text
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)
        pred = torch.argmax(probs, dim=1).item()
        confidence = torch.max(probs).item()

    return {
        "label": label_mapping[pred],
        "confidence": round(confidence, 4)
    }

@app.post("/classify_batch")
def classify_batch(input_data: BatchInput):
    """Classify multiple texts for bias"""
    texts = input_data.texts
    inputs = tokenizer(texts, return_tensors="pt", truncation=True, padding=True, max_length=256)
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

    results = []
    for i, text in enumerate(texts):
        label = label_mapping[preds[i].item()]
        confidence = torch.max(probs[i]).item()
        results.append({
            "text": text,
            "label": label,
            "confidence": round(confidence, 4)
        })
    return {"results": results}

# --- RECOMMENDATION FUNCTIONS ---
def extract_keywords(text, top_n=3):
    """Extract top keywords from text"""
    if not text or len(text.strip()) < 10:
        return []

    try:
        keywords = kw_model.extract_keywords(text, top_n=top_n)
        return [word for word, _ in keywords]
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        return []

def search_and_classify(query, limit=25):
    """
    Search Reddit using their built-in 'top' sort.
    """
    if not query or not query.strip():
        return []

    try:
        results = reddit.subreddit("all").search(query, sort="top", limit=limit)
        posts = []

        for post in results:
            text = f"{post.title} {post.selftext}"
            leaning = classifier(text)
            posts.append({
                "title": post.title,
                "leaning": leaning,
                "url": f"https://www.reddit.com{post.permalink}",
                "upvotes": post.score,
                "comments": post.num_comments,
                "subreddit": post.subreddit.display_name
            })

        return posts
    except Exception as e:
        print(f"Search error: {e}")
        return []

def find_counter_posts(latest_post_text, bias):
    """Find 2 neutral posts + 2 opposite leaning posts"""
    keywords = extract_keywords(latest_post_text)
    if not keywords:
        print("No keywords found")
        return []

    print(f"Keywords: {keywords}")
    query = " ".join(keywords)

    posts = search_and_classify(query, limit=50)

    neutral_posts = [p for p in posts if p["leaning"] == "neutral"]
    target_leaning = "right" if bias == "left" else "left"
    opposite_posts = [p for p in posts if p["leaning"] == target_leaning]

    print(f"Found {len(neutral_posts)} neutral posts")
    print(f"Found {len(opposite_posts)} {target_leaning}-leaning posts")

    selected_neutral = neutral_posts[:2]
    selected_opposite = opposite_posts[:2]

    recommendations = selected_neutral + selected_opposite

    print(f"Returning {len(recommendations)} total posts (2 neutral + 2 opposite)")
    return recommendations

# --- RECOMMENDATION ENDPOINTS ---
@app.post("/api/related")
def related_posts(request: RelatedRequest, db: Session = Depends(get_db)):
    """
    Get related posts from opposite leaning and neutral.
    Use this endpoint to update your database.
    
    Required fields:
    - user_id: string
    - title: string
    - post: string (post body/content)
    - label: string ('left', 'right' or 'neutal')
    - subreddit: string
    
    Returns: 
    - left/right leaning: 2 neutral posts + 2 opposite leaning posts
    - neutral: 2 neutral posts + 1 left + 1 right leaning posts
    """
    try:
        # Validate all required fields
        user_id = request.user_id
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code = 400)

        title = request.title
        post = request.post
        text = (title + " " + post).strip()

        leaning = request.label
        if not leaning:
            return JSONResponse({"error": "label required"}, status_code = 400)

        if leaning not in ["left", "right", "neutral"]:
            return JSONResponse({"error": "label must be 'left', 'right' or 'neutral' for related posts"}, status_code = 400)

        subreddit = request.subreddit
        if not subreddit:
            return JSONResponse({"error": "subreddit required"}, status_code = 400)

        if not text:
            return JSONResponse({"error": "title or post required"}, status_code = 400)

        print(f"\n{'='*50}")
        print(f"Related posts request")
        print(f"User: {user_id} | Subreddit: {subreddit}")
        print(f"Label: {leaning} | Text: {text[:80]}...")

        # Extract keywords
        keywords = extract_keywords(text)
        if not keywords:
            print("No keywords found")
            return {"related_posts": []}

        print(f"Keywords: {keywords}")
        query = " ".join(keywords)

        # Search Reddit
        posts = search_and_classify(query, limit=50)

        # Separate posts by leaning
        neutral_posts = [p for p in posts if p["leaning"] == "neutral"]
        left_posts = [p for p in posts if p["leaning"] == "left"]
        right_posts = [p for p in posts if p["leaning"] == "right"]

        print(f"Found {len(neutral_posts)} neutral posts")
        print(f"Found {len(left_posts)} {left_posts}-leaning posts")
        print(f"Found {len(right_posts)} {right_posts}-leaning posts")

        # Get related posts
        if leaning == "left":
            selected_neutral = neutral_posts[:2]
            selected_opposite = right_posts[:2]
        elif leaning == "right":
            selected_neutral = neutral_posts[:2]
            selected_opposite = left_posts[:2]
        else:
            selected_neutral = neutral_posts[:2]
            selected_opposite = left_posts[:1] + right_posts[:1]

        # Combine: 
        related = selected_neutral + selected_opposite

        print(f"Returning {len(related)} total posts (2 neutral + 2 opposite)")

        # Insert related posts into the database
        try:
            query_insert = insert(user_activity).values(
                user_id=user_id,
                title=title,
                body=post,
                bias_label=leaning,
                subreddit=subreddit,
                threshold_reached=False,
                recommendation_triggered=False,
                recommended_post_urls=json.dumps([p['url'] for p in related])
            )
            db.execute(query_insert)
            db.commit()
        except Exception as db_error:
            db.rollback()
            print(f"Database error: {db_error}")
            return JSONResponse({"error": "Database insertion failed", "details": str(db_error)}, status_code=500)

        # Return posts
        return {
            "related_posts": related  
        }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code = 500)

@app.post("/api/recommend")
def recommend(request: RecommendRequest, db: Session = Depends(get_db)):
    """
    Main recommendation endpoint based on user bias tracking.
    
    Required fields:
    - user_id: string
    - title: string
    - post: string (post body/content)
    - label: string ('left', 'right', or 'neutral')
    - subreddit: string (optional, for updates)
    
    Returns: 2 neutral posts + 2 opposite leaning posts when bias threshold reached
    """
    try:
        # Validate all required fields
        title = request.title
        post = request.post
        text = (title + " " + post).strip()

        leaning = request.label
        if not leaning:
            return JSONResponse({"error": "label required"}, status_code = 400)

        if leaning not in ["left", "right", "neutral"]:
            return JSONResponse({"error": "label must be 'left', 'right', or 'neutral'"}, status_code = 400)

        if not text:
            return JSONResponse({"error": "title or post required"}, status_code = 400)

        print(f"\n{'='*50}")
        print(f"Recommend request")
        print(f"Label: {leaning} | Text: {text[:80]}...")

        # For tracking purposes, we need some identifier
        user_id = request.user_id
        if not user_id:
            return JSONResponse({"error": "user_id is required"}, status_code = 400)

        # Classify the post using the bias detection model
        leaning = classifier(text)

        # REMOVED: Database insertion (handled by /api/related instead)
        # This prevents duplicate records
        
        # Update bias counts
        if leaning in ["left", "right"]:
            user_bias_data[user_id][leaning] += 1

        left_count = user_bias_data[user_id]["left"]
        right_count = user_bias_data[user_id]["right"]
        print(f"Counts - Left: {left_count}, Right: {right_count}")

        # Check bias threshold
        bias = None
        if left_count >= BIAS_THRESHOLD:
            bias = "left"
            print(f"BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}
        elif right_count >= BIAS_THRESHOLD:
            bias = "right"
            print(f"BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}

        # Return response
        if bias:
            # Get 2 neutral + 2 opposite recommendations
            recommendations = find_counter_posts(text, bias)
            
            # Insert recommendation info into the database
            recommended_urls = [rec['url'] for rec in recommendations[:4]]  # Top 4 recommended posts
            
            # Update the MOST RECENT record for this user/title combination
            # This updates the record that was created by /api/related
            try:
                from sqlalchemy import and_
                
                update_query = user_activity.update().where(
                    and_(
                        user_activity.c.user_id == user_id,
                        user_activity.c.title == title
                    )
                ).values(
                    threshold_reached=True,
                    recommendation_triggered=True,
                    recommended_post_urls=json.dumps(recommended_urls)
                ).order_by(user_activity.c.timestamp.desc()).limit(1)
                
                db.execute(update_query)
                db.commit()
                print(f"Updated existing record with recommendations")
            except Exception as db_error:
                db.rollback()
                print(f"Database update error: {db_error}")
                # Don't fail the request if update fails, just log it
            
            return {
                "user_id": user_id,
                "status": "bias_detected",
                "bias_detected": True,
                "bias": bias,
                "recommendations": recommendations  # 2 neutral + 2 opposite
            }

        return Response(status_code = 204)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code = 500)

# --- HEALTH AND ROOT ENDPOINTS ---
@app.get("/")
def home():
    return {
        "message": "Combined Bias Detection and Recommendation API is running!",
        "available_endpoints": {
            "classification": ["/classify", "/classify_batch"],
            "recommendation": ["/api/related", "/api/recommend"],
            "health": ["/health", "/api/health"]
        }
    }

@app.get("/health")
@app.get("/api/health")
def health():
    """Check if API is running"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "reddit_connected": reddit is not None,
        "service": "combined_bias_detection_recommendation"
    }

# --- RUN APP ---
if __name__ == "__main__":
    uvicorn.run("combined_api:app", host="0.0.0.0", port=8000, reload=True)
