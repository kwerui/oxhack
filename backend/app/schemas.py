from typing import Annotated
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    presetId: str = "balanced-portfolio"
    branchName: Annotated[str, Field(min_length=1, max_length=48)] = "Base case"
    seed: Annotated[int, Field(ge=0, le=2_147_483_647)] = 42
    runs: Annotated[int, Field(ge=100, le=50_000)] = 5_000
    horizonYears: Annotated[int, Field(ge=1, le=50)] = 10
    initialValue: Annotated[float, Field(ge=0, le=10_000_000)] = 10_000
    annualContribution: Annotated[float, Field(ge=0, le=1_000_000)] = 2_000
    expectedAnnualReturn: Annotated[float, Field(ge=-0.95, le=1.0)] = 0.06
    annualVolatility: Annotated[float, Field(ge=0.001, le=2.0)] = 0.12
    inflationRate: Annotated[float, Field(ge=-0.5, le=1.0)] = 0.025
    targetValue: Annotated[float, Field(ge=0, le=100_000_000)] = 40_000


class Preset(BaseModel):
    id: str
    name: str
    description: str
    defaults: dict[str, float | int]


class Metric(BaseModel):
    label: str
    value: float
    format: str
    detail: str


class SimulationResponse(BaseModel):
    id: str
    branchName: str
    seed: int
    runs: int
    horizonYears: int
    inputs: dict[str, float | int | str]
    percentiles: dict[str, float]
    histogram: list[dict[str, float | int]]
    metrics: list[Metric]
    assumptions: list[str]
    caveats: list[str]
