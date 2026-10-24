# Implementation Plan: TimeFork

This starter is organised around a simulation contract first, then a single visual comparison flow. The API is stateless and local, avoiding premature persistence and credentials.

## Architecture decisions

- FastAPI owns validation and deterministic NumPy calculations.
- Next.js owns branch state locally; the backend remains a compute service.
- External data is an explicitly-labelled adapter, not an implied forecasting feed.

## Risks

| Risk | Mitigation |
|---|---|
| Model output mistaken for advice | Persistent caveats, neutral labels, visible assumptions |
| External source unavailable | Offline mock with explicit source field |
| Comparison is irreproducible | Seed returned with every simulation |
