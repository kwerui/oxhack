# Spec: TimeFork hackathon starter

## Objective

TimeFork is a local web application for exploring **illustrative** decision scenarios. A user starts from a preset, changes inputs, creates named branches, and compares distributions from deterministic seeded Monte Carlo runs. The first preset is portfolio allocation; the simulation contract is domain-configurable so a STEM model can be added without changing the UI shape. It does not give financial, medical, engineering, or investment advice, and it will visibly state the model assumptions and limitations.

### Success criteria

- A user can select a preset, change numeric variables, simulate a branch, and compare it against another branch.
- The API validates inputs and produces repeatable results for the same seed and request.
- Results contain percentile outcomes, probability of loss / threshold failure, drawdown proxy, and explicit model caveats.
- The React UI presents a time-themed branch timeline, distribution chart, risk summary, loading/error/empty states, and keyboard-accessible controls.
- A World Bank-compatible data-source adapter is documented with an offline mock fallback and caveats about latency, availability, and causal interpretation.
- An AI-summary endpoint is disabled unless an environment flag is explicitly set, and works only from supplied simulation statistics.
- Unit/API tests, type checks, and local run instructions are included.

## Tech stack

- Frontend: Next.js (App Router), React, TypeScript, Recharts, Vitest.
- Backend: FastAPI, Pydantic, NumPy, pytest.
- Runtime: two local development servers; no database or external credentials needed for the MVP.

## API contract

`GET /api/v1/presets` returns configurable presets.

`POST /api/v1/simulations` accepts `presetId`, `branchName`, `seed`, `runs`, `horizonYears`, and bounded numeric overrides. It returns a simulation id, normalized inputs, histogram bins, percentiles, risk metrics, assumptions, and caveats. Invalid values produce FastAPI's consistent validation response with HTTP 422. The endpoint is compute-only and safe to retry.

`GET /api/v1/data/world-bank/{indicator}` returns a validated, documented adapter response or a local illustrative fallback. It must never silently treat external data as an active market signal.

`POST /api/v1/analysis` returns a deterministic, grounded template analysis from simulation output when `ENABLE_AI_ANALYSIS=true`; otherwise it returns 404. No external model call is required by the starter.

## Commands

```sh
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
cd backend && pytest

cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run test && npm run lint && npm run typecheck && npm run build
```

## Project structure

```text
backend/app/        FastAPI routes, schemas, engine, presets, adapters
backend/tests/      simulation and HTTP contract tests
frontend/app/       Next.js route and global styling
frontend/components/ interactive timeline, controls, charts, metrics
frontend/lib/       API client and shared types
frontend/tests/     UI/unit tests
docs/               data source, model, and safety notes
```

## Code style

Use explicit input/output models, camelCase at the JSON boundary, immutable TypeScript state updates, and small pure functions for calculations.

```ts
const nextBranch = { ...branch, inputs: { ...branch.inputs, annualContribution: value } };
```

## Testing strategy

- pytest unit tests prove seed reproducibility, sane percentile ordering, and rejection of unsafe inputs.
- FastAPI tests prove the simulation and preset contracts.
- Vitest tests cover client-side branch comparison helpers.
- `npm run typecheck`, lint, frontend build, and pytest run before delivery.

## Boundaries

- Always: validate untrusted input, label outputs illustrative, preserve seed provenance, include assumptions/caveats, run checks.
- Ask first: add third-party API credentials, persistent storage, auth, real trades/advice, or deployment infrastructure.
- Never: imply probability estimates are predictions, fabricate data availability, commit credentials, or silently fall back from a live source without labelling it.

## Open questions

- The next domain preset can be chosen after the demo: project delivery risk, climate resilience, or laboratory experiment planning.
