# Geospatial File Measurement API

FastAPI service for uploading KML files and zipped Shapefiles, extracting their features, and calculating measurements in metric units.

## Setup

Python 3.11+ is recommended.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API

### Upload

`POST /api/files/` with a multipart form field named `file`.

Accepted formats:

- `.kml`
- `.zip` containing the `.shp`, `.shx`, `.dbf`, and preferably `.prj` Shapefile companion files

Example:

```powershell
curl.exe -X POST -F "file=@survey.kml" http://127.0.0.1:8000/api/files/
```

Response:

```json
{
  "id": "a uuid-like id",
  "filename": "survey.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

### File information

`GET /api/files/{id}/` returns the summary and extracted features. Each feature includes its index, geometry type, GeoJSON geometry, source CRS, properties, and a measurement object.

### Measurements

`GET /api/files/{id}/measurements/` returns the measurements for all extracted features. Polygon and MultiPolygon features contain `area_m2`; LineString and MultiLineString features contain `length_m`; point features have no measurement; unsupported geometries contain a reason instead of causing processing to fail.

## Architecture

- `app/main.py` owns HTTP concerns, validation boundaries, and the three API routes.
- `app/geospatial.py` owns file format detection, GeoPandas ingestion, feature serialization, CRS selection, and measurements.
- `app/storage.py` provides a thread-safe in-memory store for this self-contained exercise.
- `app/models.py` defines response contracts with Pydantic.

The upload flow reads the multipart file, validates the extension and archive contents, loads it into a GeoDataFrame, transforms each measurable geometry when required, and stores the completed result by generated ID.

## CRS and measurement decisions

Measurements must not be calculated from longitude/latitude degrees. If the source CRS is geographic, the service chooses a local UTM CRS with GeoPandas `estimate_utm_crs()` and calculates area or length there. Projected source CRSs are used directly. A missing CRS is reported per feature and does not crash the upload. Measurement values are returned in square metres or metres.

The current API keeps processed data in memory to keep the example easy to run. Production deployment should use object storage for uploads, a database for metadata and results, background jobs for large files, size limits, authentication, structured logging, and a durable cache. A next iteration could add GeoJSON input, asynchronous processing status, configurable CRS strategy, pagination, and richer validation of Shapefile archives.

## Learning and future scope

This project demonstrates the boundary between HTTP upload handling and geospatial computation, including the importance of projected CRSs for metric calculations. Future learning areas include GDAL driver portability, topology validation, large-file streaming, spatial indexing, and operational deployment of geospatial dependencies.
