import pytest
import json
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app import load_pois, save_pois, PoiIn
from app import app
import uuid
from unittest.mock import AsyncMock, patch
import asyncio

ORIGINAL_BASE_DIR = Path(__file__).parent


class TestTravelPlanner:

    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_base_dir = Path(self.temp_dir.name)

        self.test_pois_file = self.test_base_dir / "pois.json"
        with open(self.test_pois_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)

        import app
        app.BASE_DIR = self.test_base_dir

    def teardown_method(self):
        self.temp_dir.cleanup()
        import app
        app.BASE_DIR = ORIGINAL_BASE_DIR

    def test_load_pois_empty_file(self):
        pois = load_pois()
        assert pois == []

    def test_load_pois_with_data(self):
        test_data = [{"id": "1", "name": "Test POI", "lat": 55.7558, "lon": 37.6173, "tags": ["park"]}]
        with open(self.test_pois_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        pois = load_pois()
        assert len(pois) == 1
        assert pois[0]["name"] == "Test POI"

    def test_save_pois(self):
        test_data = [{"id": "1", "name": "Test POI", "lat": 55.7558, "lon": 37.6173, "tags": ["park"]}]
        save_pois(test_data)

        with open(self.test_pois_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)

        assert saved_data == test_data

    def test_poi_validation_valid_data(self):
        poi = PoiIn(name="Eiffel Tower", lat=48.8584, lon=2.2945, tags=["monument"])
        assert poi.name == "Eiffel Tower"
        assert poi.lat == 48.8584
        assert poi.lon == 2.2945

    def test_poi_validation_invalid_lat(self):
        with pytest.raises(ValueError, match="lat must be between -90 and 90"):
            PoiIn(name="Invalid", lat=100.0, lon=0.0)

    def test_poi_validation_invalid_lon(self):
        with pytest.raises(ValueError, match="lon must be between -180 and 180"):
            PoiIn(name="Invalid", lat=0.0, lon=200.0)


class TestPOIEndpoints:

    def setup_method(self):
        from app import app
        self.client = TestClient(app)
        self.test_poi = {
            "name": "Test Attraction",
            "lat": 55.7558,
            "lon": 37.6173,
            "tags": ["museum", "culture"]
        }

        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_base_dir = Path(self.temp_dir.name)

        self.test_pois_file = self.test_base_dir / "pois.json"
        with open(self.test_pois_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)

        import app
        app.BASE_DIR = self.test_base_dir

    def teardown_method(self):
        self.temp_dir.cleanup()
        import app
        app.BASE_DIR = ORIGINAL_BASE_DIR

    def test_create_poi_success(self):
        response = self.client.post("/pois", json=self.test_poi)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Attraction"
        assert "id" in data
        assert data["lat"] == 55.7558
        assert data["lon"] == 37.6173

    def test_create_poi_duplicate_name(self):
        response1 = self.client.post("/pois", json=self.test_poi)
        assert response1.status_code == 201

        response2 = self.client.post("/pois", json=self.test_poi)
        assert response2.status_code == 409
        assert "уже существует" in response2.json()["detail"]

    def test_list_pois(self):
        create_response = self.client.post("/pois", json=self.test_poi)
        assert create_response.status_code == 201

        response = self.client.get("/pois")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Attraction"

    def test_delete_poi_success(self):
        create_response = self.client.post("/pois", json=self.test_poi)
        poi_id = create_response.json()["id"]

        response = self.client.delete(f"/pois/{poi_id}")
        assert response.status_code == 204

        list_response = self.client.get("/pois")
        pois = list_response.json()
        assert len(pois) == 0

    def test_delete_poi_not_found(self):
        response = self.client.delete("/pois/nonexistent")
        assert response.status_code == 404


class TestGeocodeEndpoint:

    def setup_method(self):
        from app import app
        self.client = TestClient(app)

    @patch('app.httpx.AsyncClient')
    def test_geocode_success(self, mock_client):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [{
                "geometry": {
                    "type": "Point",
                    "coordinates": [37.6173, 55.7558]  # ORS: [lon, lat]
                },
                "properties": {
                    "label": "Moscow, Russia",
                    "name": "Moscow"
                }
            }]
        }

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_async_client

        response = self.client.get("/geocode?q=Moscow")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["label"] == "Moscow, Russia"
        assert data["results"][0]["lat"] == 55.7558
        assert data["results"][0]["lon"] == 37.6173

    @patch('app.httpx.AsyncClient')
    def test_geocode_error(self, mock_client):
        """Тест геокодирования с ошибкой"""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value.get.return_value = mock_response
        mock_client.return_value = mock_async_client

        response = self.client.get("/geocode?q=InvalidPlace")

        assert response.status_code == 500


class TestRouteEndpoint:

    def setup_method(self):
        from app import app
        self.client = TestClient(app)

    @patch('app.httpx.AsyncClient')
    def test_route_success(self, mock_client):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "features": [{
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[2.2945, 48.8584], [2.3376, 48.8606]]
                },
                "properties": {
                    "summary": {
                        "distance": 3500.0,  # 3.5 km in meters
                        "duration": 2700.0  # 45 minutes in seconds
                    }
                }
            }]
        }

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_async_client

        from_coord = "48.8584,2.2945"
        to_coord = "48.8606,2.3376"
        response = self.client.get(f"/route?from_coord={from_coord}&to_coord={to_coord}")

        assert response.status_code == 200
        data = response.json()
        assert "geojson" in data
        assert "distance_km" in data
        assert "duration_min" in data
        assert data["distance_km"] == 3.5
        assert data["duration_min"] == 45

    def test_route_invalid_coordinates(self):
        response = self.client.get("/route?from_coord=invalid&to_coord=48.8606,2.3376")
        assert response.status_code == 400


class TestEdgeCases:

    def setup_method(self):
        from app import app
        self.client = TestClient(app)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_base_dir = Path(self.temp_dir.name)

        self.test_pois_file = self.test_base_dir / "pois.json"
        with open(self.test_pois_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False)

        import app
        app.BASE_DIR = self.test_base_dir

    def teardown_method(self):
        self.temp_dir.cleanup()
        import app
        app.BASE_DIR = ORIGINAL_BASE_DIR

    def test_create_poi_with_special_characters(self):
        test_poi = {
            "name": "Café & Restaurant 🍕",
            "lat": 48.8566,
            "lon": 2.3522,
            "tags": ["food", "restaurant"]
        }

        response = self.client.post("/pois", json=test_poi)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Café & Restaurant 🍕"

    def test_create_poi_empty_tags(self):
        test_poi = {
            "name": "Point without tags",
            "lat": 40.7128,
            "lon": -74.0060,
            "tags": []
        }

        response = self.client.post("/pois", json=test_poi)
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--html=report.html", "--self-contained-html"])