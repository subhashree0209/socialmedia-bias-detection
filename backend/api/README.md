# Bias Detection and Recommendation System

A FastAPI-based system that detects political bias in text content and provides counter-narrative recommendations from Reddit to promote balanced information consumption.

## Features

- **Bias Classification**: Classify text as left-leaning, right-leaning, or neutral using a fine-tuned RoBERTa model
- **Batch Processing**: Classify multiple posts simultaneously
- **User Bias Tracking**: Monitor user reading patterns and detect echo chamber behavior
- **Smart Recommendations**: Suggest neutral and opposing viewpoint content when bias threshold is reached
- **Reddit Integration**: Search and classify Reddit posts for related content
- **Keyword Extraction**: Use KeyBERT to find relevant content based on post topics

## Architecture

```
        ┌─────────────────┐
        │    Frontend     │
        └────────┬────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│          FastAPI Backend            │
│  ┌──────────────┐  ┌─────────────┐  │
│  │ RoBERTa      │  │  KeyBERT    │  │
│  │ Classifier   │  │  Keywords   │  │
│  └──────────────┘  └─────────────┘  │
│  ┌──────────────────────────────┐   │
│  │      User Bias Tracker       │   │
│  └──────────────────────────────┘   │
└────────────────┬────────────────────┘
                 │
                 ▼
          ┌──────────────┐
          │  Reddit API  │
          └──────────────┘
```

## Prerequisites

- Python 3.10+
- Docker
- Reddit API credentials
- Pre-trained RoBERTa model for bias detection (Hosted on AWS)

## API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```http
GET /health
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "reddit_connected": true,
  "service": "combined_bias_detection_recommendation"
}
```

#### 2. Classify Single Text
```http
POST /classify
```

**Request Body:**
```json
{
  "text": "Your text content here"
}
```

**Response:**
```json
{
  "label": "left",
  "confidence": 0.9234
}
```

#### 3. Classify Batch
```http
POST /classify_batch
```

**Request Body:**
```json
{
  "texts": [
    "First text to classify",
    "Second text to classify"
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "text": "First text to classify",
      "label": "neutral",
      "confidence": 0.8567
    },
    {
      "text": "Second text to classify",
      "label": "right",
      "confidence": 0.9123
    }
  ]
}
```

#### 4. Get Related Posts
```http
POST /api/related
```

**Purpose:** Get related posts for database updates. Returns 2 neutral + 2 opposite-leaning posts (or 2 neutral + 1 left + 1 right for neutral posts).

**Request Body:**
```json
{
  "user_id": "user123",
  "title": "Post title",
  "post": "Post content",
  "label": "left",
  "subreddit": "politics"
}
```

**Response:**
```json
{
  "related_posts": [
    {
      "title": "Related post title",
      "leaning": "neutral",
      "url": "https://www.reddit.com/r/...",
      "upvotes": 1234,
      "comments": 56,
      "subreddit": "neutralpolitics"
    }
  ]
}
```

#### 5. Get Recommendations (Bias-based)
```http
POST /api/recommend
```

**Purpose:** Track user bias and provide counter-narrative recommendations when threshold (20 posts) is reached.

**Request Body:**
```json
{
  "user_id": "user123",
  "title": "Post title",
  "post": "Post content",
  "label": "left"
}
```

**Response (when bias threshold NOT reached):**
```http
HTTP 204 No Content
```

**Response (when bias threshold reached):**
```json
{
  "user_id": "user123",
  "status": "bias_detected",
  "bias_detected": true,
  "bias": "left",
  "recommendations": [
    {
      "title": "Neutral perspective post",
      "leaning": "neutral",
      "url": "https://www.reddit.com/r/...",
      "upvotes": 890,
      "comments": 34,
      "subreddit": "neutralnews"
    },
    {
      "title": "Alternative viewpoint post",
      "leaning": "right",
      "url": "https://www.reddit.com/r/...",
      "upvotes": 456,
      "comments": 23,
      "subreddit": "conservative"
    }
  ]
}
```

## Configuration

### Bias Threshold
Default threshold for triggering recommendations: **20 posts**

To change, modify in `combined_api.py`:
```python
BIAS_THRESHOLD = 20  # Change this value
```

### Keyword Extraction
Default number of keywords extracted: **3**

Modify in the `extract_keywords()` function:
```python
def extract_keywords(text, top_n=3):  # Change top_n
```

### Search Limits
Default Reddit search limit: **50 posts**

Modify in `search_and_classify()`:
```python
results = reddit.subreddit("all").search(query, sort="top", limit=50)
```

## 📦 Project Structure

```
.
├── combined_api.py                      # Main FastAPI application
├── requirements.txt                     # Python dependencies
├── Dockerfile                           # Docker configuration
├── .env                                 # Environment variables (create this)
├── .gitignore
├── .dockerignore
└── README.md                            
```

## 🧪 Testing

### Using cURL

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

**Test classification:**
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test article about politics"}'
```

**Test recommendations:**
```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "title": "Test Post",
    "post": "Test content",
    "label": "left"
  }'
```

### Using Python Requests

```python
import requests

# Classify text
response = requests.post(
    "http://localhost:8000/classify",
    json={"text": "Your text here"}
)
print(response.json())

# Get recommendations
response = requests.post(
    "http://localhost:8000/api/recommend",
    json={
        "user_id": "user123",
        "title": "Article title",
        "post": "Article content",
        "label": "left"
    }
)
print(response.json())
```

## Security Considerations

- Store Reddit API credentials in environment variables, never in code
- Use HTTPS in production
- Implement rate limiting for production deployments
- Add authentication/authorization for user-specific endpoints
- Validate and sanitize all user inputs

## Label Mapping

| Label | Meaning |
|-------|---------|
| `left` | Left-leaning political bias |
| `neutral` | Neutral/balanced content |
| `right` | Right-leaning political bias |

## Troubleshooting

### Model Loading Issues
- Ensure the model directory path is correct
- Verify all model files are present
- Check Python has read permissions

### Reddit API Errors
- Verify your credentials in `.env`
- Check your Reddit app is active
- Ensure you're not exceeding API rate limits

### CORS Issues
- The API allows all origins by default
- Modify `CORSMiddleware` settings in `combined_api.py` for production

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in code
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request