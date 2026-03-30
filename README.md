# Football Form Guide

RAG-powered football tactics and stats chatbot.

## Dev setup

### Backend
```bash
source venv/bin/activate  # run from project root
cd backend/api
uvicorn main:app --reload
```
Runs on `http://localhost:8000`

### Frontend
```bash
cd frontend
npm run dev
```
Runs on `http://localhost:5173`
