from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import mapping

from .models import FeatureResponse, Measurement

SUPPORTED_EXTENSIONS = {".kml", ".zip"}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return json.loads(json.dumps(value, default=str))


def _crs_name(crs: Any) -> str | None:
    if crs is None:
        return None
    return crs.to_string()


def _extract_zip_safely(archive: zipfile.ZipFile, destination: Path) -> None:
    destination_root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if destination_root not in target.parents and target != destination_root:
            raise ValueError("ZIP archive contains an unsafe path")
    archive.extractall(destination)


def _load_geodataframe(filename: str, content: bytes) -> gpd.GeoDataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only .kml files and .zip Shapefile archives are supported")

    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / Path(filename).name
        source.write_bytes(content)
        if suffix == ".zip":
            if not zipfile.is_zipfile(source):
                raise ValueError("Uploaded .zip file is not a valid ZIP archive")
            with zipfile.ZipFile(source) as archive:
                names = [name for name in archive.namelist() if not name.endswith("/")]
                if not any(Path(name).suffix.lower() == ".shp" for name in names):
                    raise ValueError("ZIP archive must contain a Shapefile (.shp)")
                _extract_zip_safely(archive, Path(temp_dir))
                shp_path = next(Path(temp_dir).rglob("*.shp"))
            return gpd.read_file(shp_path)
        return gpd.read_file(source, driver="KML")


def _measurement(geometry: Any, source_crs: Any) -> Measurement:
    if geometry is None or geometry.is_empty:
        return Measurement(reason="Geometry is empty")
    geometry_type = geometry.geom_type
    if geometry_type not in {"Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point", "MultiPoint"}:
        return Measurement(reason=f"Measurement is not supported for {geometry_type}")
    if geometry_type in {"Point", "MultiPoint"}:
        return Measurement(reason="No measurement is required for point geometry")
    if source_crs is None:
        return Measurement(reason="Source CRS is missing; measurement was not calculated")

    measurement_crs = source_crs
    if source_crs.is_geographic:
        measurement_crs = gpd.GeoSeries([geometry], crs=source_crs).estimate_utm_crs()
    if measurement_crs is None:
        return Measurement(reason="Unable to select a projected CRS for measurement")
    projected = gpd.GeoSeries([geometry], crs=source_crs).to_crs(measurement_crs).iloc[0]
    if geometry_type in {"Polygon", "MultiPolygon"}:
        return Measurement(area_m2=float(projected.area))
    return Measurement(length_m=float(projected.length))


def process_file(filename: str, content: bytes) -> tuple[str | None, list[FeatureResponse]]:
    dataframe = _load_geodataframe(filename, content)
    source_crs = dataframe.crs
    crs = _crs_name(source_crs)
    features: list[FeatureResponse] = []
    for index, row in dataframe.iterrows():
        geometry = row.geometry
        properties = {key: _json_safe(value) for key, value in row.items() if key != dataframe.geometry.name}
        features.append(
            FeatureResponse(
                id=int(index) if isinstance(index, (int, float)) else len(features),
                geometry_type=geometry.geom_type if geometry is not None else "Unknown",
                geometry=mapping(geometry) if geometry is not None and not geometry.is_empty else None,
                crs=crs,
                properties=properties,
                measurement=_measurement(geometry, source_crs),
            )
        )
    return crs, features
