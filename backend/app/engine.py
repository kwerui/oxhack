import hashlib
import numpy as np
from .schemas import Metric, SimulationRequest, SimulationResponse


def _money_histogram(values: np.ndarray, bins: int = 18) -> list[dict[str, float | int]]:
    counts, edges = np.histogram(values, bins=bins)
    return [
        {"start": round(float(edges[i]), 2), "end": round(float(edges[i + 1]), 2), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def simulate(request: SimulationRequest) -> SimulationResponse:
    rng = np.random.default_rng(request.seed)
    value = np.full(request.runs, request.initialValue, dtype=float)
    peak = value.copy()
    max_drawdown = np.zeros(request.runs)
    for _ in range(request.horizonYears):
        annual_return = rng.normal(request.expectedAnnualReturn, request.annualVolatility, request.runs)
        value = np.maximum(0, value * (1 + annual_return) + request.annualContribution)
        peak = np.maximum(peak, value)
        max_drawdown = np.maximum(max_drawdown, (peak - value) / np.maximum(peak, 1))

    real_value = value / ((1 + request.inflationRate) ** request.horizonYears)
    p10, p50, p90 = np.percentile(real_value, [10, 50, 90])
    loss_probability = float(np.mean(real_value < request.initialValue))
    target_probability = float(np.mean(real_value >= request.targetValue))
    average_drawdown = float(np.mean(max_drawdown))
    digest = hashlib.sha256(f"{request.model_dump_json()}".encode()).hexdigest()[:12]
    metrics = [
        Metric(label="Target reached", value=target_probability, format="percent", detail="Share of simulated paths at or above your target."),
        Metric(label="Value below start", value=loss_probability, format="percent", detail="Share of inflation-adjusted paths below the starting value."),
        Metric(label="Median end value", value=float(p50), format="currency", detail="50th percentile, inflation-adjusted."),
        Metric(label="Average max drawdown", value=average_drawdown, format="percent", detail="Modelled peak-to-trough decline across each path."),
    ]
    return SimulationResponse(
        id=digest,
        branchName=request.branchName,
        seed=request.seed,
        runs=request.runs,
        horizonYears=request.horizonYears,
        inputs=request.model_dump(),
        percentiles={"p10": round(float(p10), 2), "p50": round(float(p50), 2), "p90": round(float(p90), 2)},
        histogram=_money_histogram(real_value),
        metrics=metrics,
        assumptions=["Annual returns are independent normal samples.", "Contributions occur once at each year end.", "Values are shown in today's money using the selected inflation rate."],
        caveats=["This is an illustrative sensitivity model, not a prediction or recommendation.", "Historical or external data cannot establish future returns or causal outcomes.", "Tail events, fees, taxes, changing correlations, and behavioural choices are excluded."],
    )
