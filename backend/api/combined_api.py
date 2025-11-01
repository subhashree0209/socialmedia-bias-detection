# --- IMPORTS ---
from fastapi import FastAPI, Request, Response
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

# --- FASTAPI APP ---
app = FastAPI(title="Bias Detection and Recommendation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOAD MODELS ---
model_path = './bias_detection_model_roberta'
tokenizer = RobertaTokenizer.from_pretrained(model_path)
model = RobertaForSequenceClassification.from_pretrained(model_path)
model.eval()

# Label mapping for classification
label_mapping = {0: "left", 1: "neutral", 2: "right"}

# --- KEYWORD MODEL ---
kw_model = KeyBERT()

# --- USER BIAS TRACKER ---
user_bias_data = defaultdict(lambda: {"left": 0, "right": 0})
BIAS_THRESHOLD = 20

# --- REDDIT API ---
load_dotenv()

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

def search_and_classify(query, limit=50):
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
def related_posts(request: RelatedRequest):
    """
    Get related posts from opposite leaning and neutral.
    Use this endpoint to update your database.
    """
    try:
        user_id = request.user_id
        if not user_id:
            return JSONResponse({"error": "user_id required"}, status_code=400)

        title = request.title
        post = request.post
        text = (title + " " + post).strip()

        leaning = request.label
        if not leaning:
            return JSONResponse({"error": "label required"}, status_code=400)

        if leaning not in ["left", "right", "neutral"]:
            return JSONResponse({"error": "label must be 'left', 'right' or 'neutral' for related posts"}, status_code=400)

        subreddit = request.subreddit
        if not subreddit:
            return JSONResponse({"error": "subreddit required"}, status_code=400)

        if not text:
            return JSONResponse({"error": "title or post required"}, status_code=400)

        print(f"\n{'='*50}")
        print(f"Related posts request")
        print(f"User: {user_id} | Subreddit: {subreddit}")
        print(f"Label: {leaning} | Text: {text[:80]}...")

        keywords = extract_keywords(text)
        if not keywords:
            print("No keywords found")
            return {"related_posts": []}

        print(f"Keywords: {keywords}")
        query = " ".join(keywords)

        posts = search_and_classify(query, limit=50)

        neutral_posts = [p for p in posts if p["leaning"] == "neutral"]
        left_posts = [p for p in posts if p["leaning"] == "left"]
        right_posts = [p for p in posts if p["leaning"] == "right"]

        print(f"Found {len(neutral_posts)} neutral posts")
        print(f"Found {len(left_posts)} left-leaning posts")
        print(f"Found {len(right_posts)} right-leaning posts")

        if leaning == "left":
            selected_neutral = neutral_posts[:2]
            selected_opposite = right_posts[:2]
        elif leaning == "right":
            selected_neutral = neutral_posts[:2]
            selected_opposite = left_posts[:2]
        else:
            selected_neutral = neutral_posts[:2]
            selected_opposite = left_posts[:1] + right_posts[:1]

        related = selected_neutral + selected_opposite

        print(f"Returning {len(related)} total posts (2 neutral + 2 opposite)")

        return {
            "related_posts": related  
        }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/recommend")
def recommend(request: RecommendRequest):
    """
    Main recommendation endpoint based on user bias tracking.
    """
    try:
        title = request.title
        post = request.post
        text = (title + " " + post).strip()

        leaning = request.label
        if not leaning:
            return JSONResponse({"error": "label required"}, status_code=400)

        if leaning not in ["left", "right", "neutral"]:
            return JSONResponse({"error": "label must be 'left', 'right', or 'neutral'"}, status_code=400)

        if not text:
            return JSONResponse({"error": "title or post required"}, status_code=400)

        print(f"\n{'='*50}")
        print(f"Recommend request")
        print(f"Label: {leaning} | Text: {text[:80]}...")

        user_id = request.user_id
        if not user_id:
            return JSONResponse({"error": "user_id is required"}, status_code=400)
        
        if leaning in ["left", "right"]:
            user_bias_data[user_id][leaning] += 1

        left_count = user_bias_data[user_id]["left"]
        right_count = user_bias_data[user_id]["right"]
        print(f"Counts - Left: {left_count}, Right: {right_count}")

        bias = None
        if left_count >= BIAS_THRESHOLD:
            bias = "left"
            print(f"BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}
        elif right_count >= BIAS_THRESHOLD:
            bias = "right"
            print(f"BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}

        if bias:
            recommendations = find_counter_posts(text, bias)
            return {
                "user_id": user_id,
                "status": "bias_detected",
                "bias_detected": True,
                "bias": bias,
                "recommendations": recommendations
            }

        return Response(status_code=204)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

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
    print("\n Starting Combined Bias Detection and Recommendation API")
    print("=" * 60)
    print("Endpoint purposes:")
    print("/classify - Classify single text for bias")
    print("/classify_batch - Classify multiple texts for bias")
    print("/api/related - Use this to update database (requires user_id, title, post, label, subreddit)")
    print("/api/recommend - Get recommendations based on bias tracking (requires title, post, label)")
    print("=" * 60)
    print("left/right leaning posts returns related posts: 2 neutral + 2 opposite leaning posts")
    print("neutral postsreturns related posts: 2 neutral + 1 of each leaning post")
    print("=" * 60 + "\n")
    print("Note: Make sure to update your frontend to use port 8000")
    print("=" * 60 + "\n")

    uvicorn.run("combined_api:app", host="0.0.0.0", port=8000, reload=True)