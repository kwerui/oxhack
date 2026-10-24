# TimeFork

TimeFork is a hackathon-ready decision-scenario explorer. It lets people fork named futures, change assumptions, and compare reproducible Monte Carlo outcome distributions. The default portfolio preset is illustrative; the included research-project preset demonstrates the same interface for broader STEM decisions.

> **Important:** TimeFork is an uncertainty and sensitivity tool, not a prediction engine. It does not provide financial, medical, engineering, or investment advice.

## What is included

- Polished Next.js/TypeScript dashboard with branching timeline, risk cards, outcome distribution bars, accessible inputs, and clear empty/error states.
- FastAPI/NumPy simulation engine with seeded reproducibility, input validation, percentiles, target probability, loss probability, and a drawdown proxy.
- Two presets with a shared configurable schema.
- Optional grounded analysis endpoint protected by `ENABLE_AI_ANALYSIS=true` (no LLM/key required for the starter).
- A World Bank-shaped mock data adapter and responsible-data guidance.
- API and engine tests.

## Run locally

Use two terminals:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```sh
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

## Verify

```sh
cd backend && pytest
cd frontend && npm run test && npm run typecheck && npm run lint && npm run build
```

Use Python 3.10 or newer. The requirements deliberately allow a current NumPy release so recent Python versions can install a compatible wheel.

## Design decisions

Each request includes a seed; same inputs plus seed produce the same sampled result. The model uses independent normally distributed annual returns, applies annual contributions, then adjusts final values for selected inflation. This makes comparisons explainable but is a deliberate simplification—see model caveats in the UI.

World Bank integration is mocked by default. Read [docs/data-sources.md](docs/data-sources.md) before replacing it with a live request.
