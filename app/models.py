from typing import Any

from pydantic import BaseModel, ConfigDict


class Measurement(BaseModel):
    area_m2: float | None = None
    length_m: float | None = None
    reason: str | None = None


class FeatureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    geometry_type: str
    geometry: dict[str, Any] | None
    crs: str | None
    properties: dict[str, Any]
    measurement: Measurement


class FileSummary(BaseModel):
    id: str
    filename: str
    feature_count: int
    crs: str | None
    status: str


class FileDetail(FileSummary):
    features: list[FeatureResponse]


class MeasurementResponse(BaseModel):
    id: str
    filename: str
    crs: str | None
    measurements: list[FeatureResponse]
