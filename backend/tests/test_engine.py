from app.engine import simulate
from app.schemas import SimulationRequest

def test_seeded_runs_are_reproducible():
    request = SimulationRequest(seed=7, runs=250)
    assert simulate(request).percentiles == simulate(request).percentiles

def test_percentiles_are_ordered_and_histogram_has_all_paths():
    result = simulate(SimulationRequest(seed=1, runs=250))
    assert result.percentiles["p10"] <= result.percentiles["p50"] <= result.percentiles["p90"]
    assert sum(bin["count"] for bin in result.histogram) == 250
