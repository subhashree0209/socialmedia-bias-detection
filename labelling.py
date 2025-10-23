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

# ==========================
# MODEL SETUP
# ==========================
MODEL_PATH = "./bias_detection_model_roberta"
tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
model.eval()

label_mapping = {0: "center", 1: "left", 2: "right"}

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

class TextInput(BaseModel):
    text: str

class BatchInput(BaseModel):
    texts: list[str]

@app.get("/")
def home():
    return {"message": "Bias classifier API is running 🚀"}

@app.post("/classify")
def classify_single(input_data: TextInput):
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

# ==========================
# RUN LOCALLY
# ==========================
if __name__ == "__main__":
    print("🚀 Running locally at: http://127.0.0.1:8000")
    uvicorn.run("labelling:app", host="127.0.0.1", port=8000, reload=True)