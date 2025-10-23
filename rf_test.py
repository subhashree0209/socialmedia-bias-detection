# %%
# --- IMPORTS ---
from flask import Flask, request, jsonify
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
from keybert import KeyBERT
from collections import defaultdict
import praw
from dotenv import load_dotenv
import os

# --- FLASK APP ---
app = Flask(__name__)

# --- LOAD MODEL ---
model_path = './bias_detection_model_roberta'
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
    user_agent="counter_recommendation_system"
)

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
    except:
        return []

# --- SEARCH REDDIT (SIMPLIFIED - USE REDDIT'S RANKING) ---
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
                "comments": post.num_comments
            })

        return posts
    except Exception as e:
        print(f"Search error: {e}")
        return []

# --- FIND TOP 5 COUNTER POSTS ---
def find_counter_posts(latest_post_text, bias):
    """
    Find top 5 counter-posts using Reddit's own ranking system.
    No custom sorting needed - Reddit already provides 'top' posts!
    """
    # Extract keywords
    keywords = extract_keywords(latest_post_text)
    if not keywords:
        print("No keywords found")
        return []

    print(f"Keywords: {keywords}")
    query = " ".join(keywords)

    # Search Reddit (already sorted by "top")
    posts = search_and_classify(query, limit=50)

    # Filter for opposite leaning
    target_leaning = "right" if bias == "left" else "left"
    opposite_posts = [p for p in posts if p["leaning"] == target_leaning]

    print(f"Found {len(opposite_posts)} {target_leaning}-leaning posts")

    # Return top 5 (already sorted by Reddit's ranking)
    return opposite_posts[:5]

# --- MAIN ENDPOINT ---

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "🚀 Bias Detection API is running!",
        "available_endpoints": ["/api/health", "/api/recommend"]
    })

@app.route("/api/recommend", methods=["POST"])
def recommend():
    """Main recommendation endpoint"""
    try:
        # Get and validate input
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id required"}), 400

        title = data.get("title", "")
        body = data.get("body", "")
        text = (title + " " + body).strip()

        if not text:
            return jsonify({"error": "title or body required"}), 400

        print(f"\n{'='*50}")
        print(f"User: {user_id} | Text: {text[:80]}...")

        # Classify post
        leaning = classifier(text)
        print(f"Classification: {leaning}")

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
            print(f"🚨 BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}
        elif right_count >= BIAS_THRESHOLD:
            bias = "right"
            print(f"🚨 BIAS THRESHOLD REACHED: {bias}")
            user_bias_data[user_id] = {"left": 0, "right": 0}

        # Return response
        if bias:
            # Get top 5 counter-recommendations
            recommendations = find_counter_posts(text, bias)
            return jsonify({
                "status": "bias_detected",
                "bias": bias,
                "recommendations": recommendations  # Array of top 5
            })
        else:
            return jsonify({
                "leaning": leaning,
                "left_count": left_count,
                "right_count": right_count
            })

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- HEALTH CHECK ---
@app.route("/api/health", methods=["GET"])
def health():
    """Check if API is running"""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None,
        "reddit_connected": reddit is not None
    })

# --- RUN APP ---
if __name__ == "__main__":
    print("\n🚀 Starting Bias Detection API (Simplified)")
    print("=" * 50)
    print("Using Reddit's built-in 'top' ranking")
    print("Returning top 5 counter-posts")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=8000, debug=True)


