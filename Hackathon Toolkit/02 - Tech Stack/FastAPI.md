# FastAPI

## When
Python APIs, ML inference, integrations. Docs: https://fastapi.tiangolo.com/

## Minimal server (`main.py`)
```python
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

class Query(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
def analyze(q: Query):
    return {"length": len(q.text), "text": q.text}
```
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn
uvicorn main:app --reload
```
Visit http://localhost:8000/docs. Use environment variables for secrets; do not enable wildcard CORS with credentials. See [[React + TypeScript]].
