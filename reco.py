# --- IMPORTS ---
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
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy import insert
from sqlalchemy.orm import sessionmaker, Session
import json
from typing import List

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@localhost/mydatabase")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define the user_activity table
metadata = MetaData()
user_activity = Table(
    'user_activity', metadata,
    autoload_with=engine,
    autoload=True
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FASTAPI APP ---
app = FastAPI(title="Reddit Extension Backend System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Reddit, your extension, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],  # Allows all headers
)

label_mapping = {0: "neutral", 1: "left", 2: "right"}

# --- LOAD MODEL ---
model_path = './bias_detection_model_roberta'  # Update to your path
tokenizer = RobertaTokenizer.from_pretrained(model_path)
model = RobertaForSequenceClassification.from_pretrained(model_path)
model.eval()

# --- KEYWORD MODEL ---
kw_model = KeyBERT()

# --- USER BIAS TRACKER ---
user_bias_data = defaultdict(lambda: {"left": 0, "right": 0})
BIAS_THRESHOLD = 20

# --- REDDIT API ---
load_dotenv() # import client id and secret id from .env

client_id = os.getenv("REDDIT_CLIENT_ID")
secret_id = os.getenv("REDDIT_SECRET_ID")
user_agent="counter_recommendation_system"

# uncomment to check if accessed 
# print(f"Client ID: {client_id}")
# print(f"Secret ID: {secret_id}")

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=secret_id,
    user_agent=user_agent
)

# --- USING PYDANTIC FOR REQUESTS ---
class RelatedRequest(BaseModel):
    user_id:str
    title: str = ""
    post: str = ""
    label: str
    subreddit: str

class RecommendRequest(BaseModel):
    user_id:str
    title: str = ""
    post: str = ""
    label: str

class TextInput(BaseModel):
    title: str = ""
    post: str = ""

class BatchInput(BaseModel):
    titles: List[str]  # List of titles
    posts: List[str]   # List of posts

# --- CLASSIFY POST ---
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

# --- EXTRACT KEYWORDS ---
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

# --- SEARCH REDDIT (SIMPLIFIED - USING REDDIT'S RANKING) ---
def search_and_classify(query, limit=50):
    """
    Search Reddit using their built-in 'top' sort.
    No custom popularity calculation needed!
    """
    if not query or not query.strip():
        return []

    try:
        # Reddit's search already sorts by "top" - we just use their ranking
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

# --- FIND 2 NEUTRAL + 2 OPPOSITE POSTS ---
def find_counter_posts(latest_post_text, bias):
    """Find 2 neutral posts + 2 opposite leaning posts"""
    # Extract keywords
    keywords = extract_keywords(latest_post_text)
    if not keywords:
        print("No keywords found")
        return []

    print(f"Keywords: {keywords}")
    query = " ".join(keywords)

    # Search Reddit (already sorted by "top")
    posts = search_and_classify(query, limit=50)

    # Separate posts by leaning
    neutral_posts = [p for p in posts if p["leaning"] == "neutral"]
    target_leaning = "right" if bias == "left" else "left"
    opposite_posts = [p for p in posts if p["leaning"] == target_leaning]

    print(f"Found {len(neutral_posts)} neutral posts")
    print(f"Found {len(opposite_posts)} {target_leaning}-leaning posts")

    # Get top 2 from each
    selected_neutral = neutral_posts[:2]
    selected_opposite = opposite_posts[:2]

    # Combine: 2 neutral + 2 opposite
    recommendations = selected_neutral + selected_opposite

    print(f"Returning {len(recommendations)} total posts (2 neutral + 2 opposite)")
    return recommendations

# --- ROOT ENDPOINT ---
@app.get("/")
def home():
    return {
        "message": "Bias Detection API is running!",
        "available endpoints": ["/api/health", "/api/related", "/api/recommend", "/classify", "/classify_batch"]
    }

# --- POST LABELLING ENDPOINT ---
@app.post("/classify")
def classify_single(input_data: TextInput):
    text = (input_data.title + " " + input_data.post).strip()
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
    # Ensure the lists are of the same length
    if len(input_data.titles) != len(input_data.posts):
        return {"error": "Titles and posts must have the same length"}

    # Combine title and post for each item in the batch
    texts = [f"{title} {post}" for title, post in zip(input_data.titles, input_data.posts)]

    # Tokenize the combined texts
    inputs = tokenizer(texts, return_tensors="pt", truncation=True, padding=True, max_length=256)

    with torch.no_grad():
        # Perform inference on the batch
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)
        preds = torch.argmax(probs, dim=1)

    # Prepare the results
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

# --- RELATED POSTS ENDPOINT (FOR DATABASE UPDATE) ---
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

# --- MAIN RECOMMENDATION ENDPOINT ---
@app.post("/api/recommend")
def recommend(request: RecommendRequest, db: Session = Depends(get_db)):
    """
    Main recommendation endpoint based on user bias tracking.
    
    Required fields:
    - title: string
    - post: string (post body/content)
    - label: string ('left', 'right', or 'neutral')
    
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
        # In this case, we will be using user_id as the identifier
        user_id = request.user_id
        if not user_id:
            return JSONResponse({"error": "user_id is required"}, status_code = 400)

        # Classify the post using the bias detection model
        leaning = classifier(text)

        # Insert user activity into the database
        try:
            query_insert = insert(user_activity).values(
                user_id=user_id,
                title=title,
                body=post,
                bias_label=leaning,
                threshold_reached=False,
                recommendation_triggered=False
            )
            result = db.execute(query_insert)
            db.commit()
            # Get the inserted row ID for later update
            inserted_id = result.lastrowid
        except Exception as db_error:
            db.rollback()
            print(f"Database error: {db_error}")
            return JSONResponse({"error": "Database insertion failed"}, status_code=500)
        
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
            
            # Update the user_activity table with recommendation info using the inserted row ID
            try:
                update_query = user_activity.update().where(
                    user_activity.c.id == inserted_id
                ).values(
                    recommendation_triggered=True,
                    recommended_post_urls=json.dumps(recommended_urls)
                )
                db.execute(update_query)
                db.commit()
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

# --- HEALTH CHECK ---
@app.get("/api/health")
def health():
    """Check if API is running"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "reddit_connected": reddit is not None
    }

# --- RUN APP ---
if __name__ == "__main__":
    print("\n Starting Bias Detection API (Updated)")
    print("=" * 50)
    print("Endpoint purposes:")
    print("/api/related - Use this to update database (requires user_id, title, post, label, subreddit)")
    print("/api/recommend - Get recommendations based on bias tracking (requires title, post, label)")
    print("=" * 50)
    print("left/right leaning posts returns related posts: 2 neutral + 2 opposite leaning posts")
    print("neutral postsreturns related posts: 2 neutral + 1 of each leaning post")
    print("=" * 50 + "\n")

    uvicorn.run("reco:app", host="0.0.0.0", port=8000, reload=True)