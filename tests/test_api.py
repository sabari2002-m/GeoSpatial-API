from io import BytesIO

import geopandas as gpd
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

from app.main import app

client = TestClient(app)


def test_upload_and_measure_epsg4326_geometries(tmp_path):
    dataframe = gpd.GeoDataFrame(
        {"name": ["parcel", "road", "marker"]},
        geometry=[
            Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01)]),
            LineString([(0, 0), (0.01, 0)]),
            Point(0, 0),
        ],
        crs="EPSG:4326",
    )
    kml_path = tmp_path / "survey.kml"
    dataframe.to_file(kml_path, driver="KML")

    response = client.post(
        "/api/files/",
        files={"file": ("survey.kml", kml_path.read_bytes(), "application/vnd.google-earth.kml+xml")},
    )

    assert response.status_code == 201
    summary = response.json()
    assert summary["feature_count"] == 3
    assert summary["crs"] == "EPSG:4326"

    measurements = client.get(f"/api/files/{summary['id']}/measurements/").json()["measurements"]
    assert measurements[0]["measurement"]["area_m2"] > 1_000_000
    assert measurements[1]["measurement"]["length_m"] > 1_000
    assert measurements[2]["measurement"]["area_m2"] is None


def test_rejects_unsupported_extension():
    response = client.post("/api/files/", files={"file": ("notes.txt", BytesIO(b"hello"), "text/plain")})
    assert response.status_code == 400


def test_missing_file_is_404():
    assert client.get("/api/files/missing/").status_code == 404
