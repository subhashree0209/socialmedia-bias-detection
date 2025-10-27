# ===========================================
# app.py — FastAPI endpoint for Reddit Bias Classifier (Local Version)
# ===========================================

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
from dotenv import load_dotenv
import praw
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from typing import List


# ==========================
# MODEL SETUP
# ==========================
MODEL_PATH = "./bias_detection_model_roberta"
tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

label_mapping = {0: "neutral", 1: "left", 2: "right"}

# --- REDDIT API ---
load_dotenv()  # import client id and secret id from .env

client_id = os.getenv("REDDIT_CLIENT_ID")
secret_id = os.getenv("REDDIT_SECRET_ID")
user_agent = "counter_recommendation_system"

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=secret_id,
    user_agent=user_agent
)

# ==========================
# FASTAPI APP
# ==========================
app = FastAPI(title="Reddit Bias Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (Reddit, your extension, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],  # Allows all headers
)

class TextInput(BaseModel):
    title: str = ""
    post: str = ""

class BatchInput(BaseModel):
    titles: List[str]  # List of titles
    posts: List[str]   # List of posts

@app.get("/")
def home():
    return {"message": "Bias classifier API is running 🚀"}

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

# ==========================
# RUN LOCALLY
# ==========================
if __name__ == "__main__":
    print("🚀 Running locally at: http://127.0.0.1:8000")
    uvicorn.run("labelling:app", host="127.0.0.1", port=8000, reload=True)