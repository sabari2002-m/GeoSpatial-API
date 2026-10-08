from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile, status

from .geospatial import process_file
from .models import FileDetail, FileSummary, MeasurementResponse
from .storage import store

app = FastAPI(
    title="Geospatial File Measurement API",
    version="1.0.0",
    description="Upload KML files or zipped Shapefiles and inspect projected measurements.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/files/", response_model=FileSummary, status_code=status.HTTP_201_CREATED, tags=["files"])
async def upload_file(file: UploadFile = File(...)) -> FileSummary:
    filename = file.filename or "upload"
    try:
        content = await file.read()
        crs, features = process_file(filename, content)
    except (ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process geospatial file: {exc}") from exc

    detail = FileDetail(
        id=uuid4().hex,
        filename=filename,
        feature_count=len(features),
        crs=crs,
        status="COMPLETED",
        features=features,
    )
    store.save(detail)
    return FileSummary(**detail.model_dump(exclude={"features"}))


@app.get("/api/files/{file_id}/", response_model=FileDetail, tags=["files"])
def file_information(file_id: str) -> FileDetail:
    stored = store.get(file_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="File not found")
    return stored.detail


@app.get("/api/files/{file_id}/measurements/", response_model=MeasurementResponse, tags=["files"])
def file_measurements(file_id: str) -> MeasurementResponse:
    stored = store.get(file_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="File not found")
    detail = stored.detail
    return MeasurementResponse(
        id=detail.id,
        filename=detail.filename,
        crs=detail.crs,
        measurements=detail.features,
    )
