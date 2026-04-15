# SaveIt — Backend API

Python + FastAPI + yt-dlp backend for SaveIt downloader.
Supports Instagram, YouTube, and Facebook.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app with /info and /download endpoints |
| `requirements.txt` | Python dependencies |
| `render.yaml` | Render deployment config |

---

## 🚀 Deploy on Render (Step by Step)

### Step 1 — GitHub pe upload karo
1. GitHub pe naya repository banao (e.g. `saveit-backend`)
2. Ye 3 files upload karo:
   - `main.py`
   - `requirements.txt`
   - `render.yaml`

### Step 2 — Render pe deploy karo
1. https://render.com pe jao aur login karo
2. **"New +"** → **"Web Service"** click karo
3. Apna GitHub repo connect karo
4. Settings:
   - **Name:** saveit-backend
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **"Create Web Service"** click karo
6. 2-3 minute mein deploy ho jayega ✅

### Step 3 — URL milega
Render ek URL dega jaise:
`https://saveit-backend.onrender.com`

---

## 🔗 API Endpoints

### GET /
Health check
```
https://your-url.onrender.com/
```

### POST /info
Media info fetch karo (title, thumbnail, formats)
```json
POST /info
Body: { "url": "https://www.youtube.com/watch?v=..." }
```

### GET /download
Direct download URL lo
```
GET /download?url=<media_url>&format_id=<format_id>
```

---

## 🔧 Frontend mein connect karo

`downloader.html` mein ye line update karo:
```javascript
const API_BASE = "https://saveit-backend.onrender.com";
```

---

## ⚠️ Notes

- **Instagram private posts** download nahi honge (login required)
- **YouTube** sab kuch kaam karta hai
- **Facebook** public videos kaam karti hain
- Render free plan pe server 15 min baad sleep karta hai — first request slow hogi
