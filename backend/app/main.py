"""HTTP routes for the AuroraTime aurora experiment."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .aurora import DATA_PATH, FEATURES, ModelRequest, evaluate_model

app = FastAPI(title="AuroraTime", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "dataReady": DATA_PATH.exists()}


@app.get("/api/v1/aurora/variables")
def variables():
    return {"features": FEATURES, "locations": ["Tromsø", "Reykjavík"]}


@app.post("/api/v1/aurora/evaluate")
def run_model(request: ModelRequest):
    return evaluate_model(request)
