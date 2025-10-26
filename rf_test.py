# --- IMPORTS ---
from flask import Flask, request, jsonify
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
from keybert import KeyBERT
from collections import defaultdict
import praw
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- FLASK APP ---
app = Flask(__name__)

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
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent="counter_recommendation_system/1.0"
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
    except Exception as e:
        print(f"Keyword extraction error: {e}")
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
                "comments": post.num_comments,
                "subreddit": post.subreddit.display_name
            })

        return posts
    except Exception as e:
        print(f"Search error: {e}")
        return []

# --- FIND TOP 3 COUNTER POSTS ---
def find_counter_posts(latest_post_text, bias):
    """Find top 3 counter-posts from opposite leaning"""
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

    # Return top 3 (already sorted by Reddit's ranking)
    return opposite_posts[:3]

# --- MAIN ENDPOINT ---
@app.route("/api/recommend", methods=["POST"])
def recommend():
    """
    Main recommendation endpoint
    
    Required fields:
    - user_id: string
    - title: string
    - body: string (can be empty)
    - label: string ('left', 'right', or 'neutral')
    - subreddit: string
    """
    try:
        # Get and validate input
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "user_id required"}), 400

        title = data.get("title", "")
        body = data.get("body", "")
        text = (title + " " + body).strip()

        leaning = data.get("label")
        if not leaning:
            return jsonify({"error": "label required"}), 400

        if leaning not in ["left", "right", "neutral"]:
            return jsonify({"error": "label must be 'left', 'right', or 'neutral'"}), 400

        subreddit = data.get("subreddit")
        if not subreddit:
            return jsonify({"error": "subreddit required"}), 400

        if not text:
            return jsonify({"error": "title or body required"}), 400

        print(f"\n{'='*50}")
        print(f"User: {user_id} | Subreddit: {subreddit}")
        print(f"Label: {leaning} | Text: {text[:80]}...")

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
            # Get top 3 counter-recommendations
            recommendations = find_counter_posts(text, bias)
            return jsonify({
                "status": "bias_detected",
                "bias": bias,
                "recommendations": recommendations
            })

        return '', 204

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- RELATED POSTS ENDPOINT ---
@app.route("/api/related", methods=["POST"])
def related_posts():
    """
    Get 3 related posts from opposite leaning
    
    Required fields:
    - title: string
    - body: string (can be empty)
    - label: string ('left' or 'right')
    - subreddit: string
    """
    try:
        # Get and validate input
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        title = data.get("title", "")
        body = data.get("body", "")
        text = (title + " " + body).strip()

        leaning = data.get("label")
        if not leaning:
            return jsonify({"error": "label required"}), 400

        if leaning not in ["left", "right"]:
            return jsonify({"error": "label must be 'left' or 'right' for related posts"}), 400

        subreddit = data.get("subreddit")
        if not subreddit:
            return jsonify({"error": "subreddit required"}), 400

        if not text:
            return jsonify({"error": "title or body required"}), 400

        print(f"\n{'='*50}")
        print(f"Related posts request | Subreddit: {subreddit}")
        print(f"Label: {leaning} | Text: {text[:80]}...")

        # Extract keywords
        keywords = extract_keywords(text)
        if not keywords:
            print("No keywords found")
            return jsonify({"related_posts": []})

        print(f"Keywords: {keywords}")
        query = " ".join(keywords)

        # Search Reddit
        posts = search_and_classify(query, limit=30)

        # Filter for opposite leaning
        target_leaning = "right" if leaning == "left" else "left"
        opposite_posts = [p for p in posts if p["leaning"] == target_leaning]

        print(f"Found {len(opposite_posts)} {target_leaning}-leaning posts")

        # Return top 3
        return jsonify({
            "related_posts": opposite_posts[:3]
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
    print("\n Starting Bias Detection API (Updated)")
    print("=" * 50)
    print("Required fields per endpoint:")
    print("/api/recommend: user_id, title, body, label, subreddit")
    print("/api/related: title, body, label, subreddit")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=8000, debug=True)