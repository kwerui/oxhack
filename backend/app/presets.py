from .schemas import Preset

PRESETS = [
    Preset(
        id="balanced-portfolio",
        name="Balanced portfolio",
        description="Illustrative long-horizon allocation with return and volatility controls.",
        defaults={"initialValue": 10000, "annualContribution": 2000, "expectedAnnualReturn": 0.06, "annualVolatility": 0.12, "inflationRate": 0.025, "targetValue": 40000, "horizonYears": 10},
    ),
    Preset(
        id="research-project",
        name="Research project runway",
        description="A generic uncertainty template for costs, capacity, or delivery value—not a forecast.",
        defaults={"initialValue": 50000, "annualContribution": 10000, "expectedAnnualReturn": 0.04, "annualVolatility": 0.18, "inflationRate": 0.02, "targetValue": 180000, "horizonYears": 8},
    ),
]
