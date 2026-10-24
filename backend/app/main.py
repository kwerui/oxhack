import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .engine import simulate
from .presets import PRESETS
from .schemas import SimulationRequest, SimulationResponse

app = FastAPI(title="TimeFork API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/api/v1/presets")
def presets(): return PRESETS

@app.post("/api/v1/simulations", response_model=SimulationResponse)
def create_simulation(request: SimulationRequest):
    if request.presetId not in {preset.id for preset in PRESETS}:
        raise HTTPException(status_code=404, detail="Unknown preset")
    return simulate(request)

@app.get("/api/v1/data/world-bank/{indicator}")
def world_bank_source(indicator: str):
    return {
        "indicator": indicator,
        "source": "mock",
        "value": 2.5,
        "year": 2024,
        "caveat": "Illustrative offline value. Replace this adapter with a validated World Bank API fetch before displaying live data; indicators are context, not forecasts.",
    }

@app.post("/api/v1/analysis")
def risk_analysis(result: SimulationResponse):
    if os.getenv("ENABLE_AI_ANALYSIS", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="AI analysis is disabled")
    target = next(metric.value for metric in result.metrics if metric.label == "Target reached")
    return {"analysis": f"Grounded summary: this seeded model puts the selected target at {target:.0%} of paths. Compare assumptions and branches; do not interpret this as a forecast."}
