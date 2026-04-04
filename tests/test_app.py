"""
Pytest suite for ACEest Fitness & Gym Flask API (v2.2.1).
Covers: utility functions, all route responses, client management
with SQLite persistence, progress tracking, and edge-case validation.
"""

import pytest
import os
from app import app, calculate_calories, init_db, get_db, PROGRAMS, DB_NAME


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Use a temporary SQLite database for each test."""
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr("app.DB_NAME", test_db)
    init_db()
    yield
    if os.path.exists(test_db):
        os.remove(test_db)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Unit tests — pure logic
# ---------------------------------------------------------------------------

class TestCalculateCalories:
    def test_fl_reference_weight(self):
        """At the 80 kg reference, check against calorie factor."""
        assert calculate_calories(80, "Fat Loss (FL)") == int(80 * PROGRAMS["Fat Loss (FL)"]["factor"])

    def test_mg_reference_weight(self):
        assert calculate_calories(80, "Muscle Gain (MG)") == int(80 * PROGRAMS["Muscle Gain (MG)"]["factor"])

    def test_bg_reference_weight(self):
        assert calculate_calories(80, "Beginner (BG)") == int(80 * PROGRAMS["Beginner (BG)"]["factor"])

    def test_heavier_client_gets_more_calories(self):
        light = calculate_calories(60, "Muscle Gain (MG)")
        heavy = calculate_calories(100, "Muscle Gain (MG)")
        assert heavy > light

    def test_unknown_program_returns_none(self):
        assert calculate_calories(75, "XX") is None

    def test_result_is_integer(self):
        result = calculate_calories(70, "Fat Loss (FL)")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# Route tests — GET /
# ---------------------------------------------------------------------------

class TestIndexRoute:
    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_contains_brand_name(self, client):
        response = client.get("/")
        assert b"ACEest" in response.data

    def test_all_program_names_present(self, client):
        response = client.get("/")
        for key in PROGRAMS:
            assert key.encode() in response.data

    def test_version_in_page(self, client):
        response = client.get("/")
        assert b"v2.2.1" in response.data


# ---------------------------------------------------------------------------
# Route tests — GET /programs
# ---------------------------------------------------------------------------

class TestProgramsRoute:
    def test_returns_200(self, client):
        response = client.get("/programs")
        assert response.status_code == 200

    def test_returns_json(self, client):
        response = client.get("/programs")
        data = response.get_json()
        assert isinstance(data, dict)

    def test_all_keys_present(self, client):
        response = client.get("/programs")
        data = response.get_json()
        for key in ("Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"):
            assert key in data

    def test_program_has_factor_field(self, client):
        response = client.get("/programs")
        data = response.get_json()
        for program in data.values():
            assert "factor" in program


# ---------------------------------------------------------------------------
# Route tests — POST /client (v2.2.1: SQLite-backed, descriptive program key)
# ---------------------------------------------------------------------------

class TestClientRoute:
    def test_valid_fat_loss_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Ravi", "program": "Fat Loss (FL)", "age": 30, "weight": 75},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["program"] == "Fat Loss (FL)"
        assert data["client"] == "Ravi"
        assert data["calories"] == int(75 * PROGRAMS["Fat Loss (FL)"]["factor"])

    def test_valid_muscle_gain_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Priya", "program": "Muscle Gain (MG)", "weight": 65},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["program"] == "Muscle Gain (MG)"

    def test_missing_name_returns_400(self, client):
        response = client.post("/client", json={"program": "Fat Loss (FL)"})
        assert response.status_code == 400
        assert b"name" in response.data

    def test_missing_program_returns_400(self, client):
        response = client.post("/client", json={"name": "Anjali"})
        assert response.status_code == 400
        assert b"program" in response.data

    def test_unknown_program_returns_400(self, client):
        response = client.post(
            "/client", json={"name": "Test", "program": "XX"}
        )
        assert response.status_code == 400

    def test_response_includes_calories(self, client):
        response = client.post(
            "/client",
            json={"name": "Kumar", "program": "Muscle Gain (MG)", "weight": 80},
        )
        data = response.get_json()
        assert "calories" in data
        assert data["calories"] == int(80 * PROGRAMS["Muscle Gain (MG)"]["factor"])

    def test_client_stored_in_db(self, client):
        """v2.2.1: clients are persisted in SQLite."""
        client.post("/client", json={"name": "Meena", "program": "Beginner (BG)", "weight": 60})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Meena"

    def test_upsert_replaces_existing(self, client):
        """v2.2.1: INSERT OR REPLACE should update an existing client."""
        client.post("/client", json={"name": "Ravi", "program": "Fat Loss (FL)", "weight": 75})
        client.post("/client", json={"name": "Ravi", "program": "Muscle Gain (MG)", "weight": 80})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["program"] == "Muscle Gain (MG)"


# ---------------------------------------------------------------------------
# Route tests — GET /client/<name> (v2.2.1: load client)
# ---------------------------------------------------------------------------

class TestLoadClient:
    def test_load_existing_client(self, client):
        client.post("/client", json={
            "name": "Ravi", "program": "Fat Loss (FL)", "age": 30, "weight": 75,
        })
        response = client.get("/client/Ravi")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Ravi"
        assert data["age"] == 30
        assert data["calories"] == int(75 * PROGRAMS["Fat Loss (FL)"]["factor"])

    def test_load_missing_client(self, client):
        response = client.get("/client/Nobody")
        assert response.status_code == 404
        assert b"not found" in response.data


# ---------------------------------------------------------------------------
# Route tests — GET /clients (v2.2.1: SQLite-backed list)
# ---------------------------------------------------------------------------

class TestClientsListRoute:
    def test_empty_list(self, client):
        response = client.get("/clients")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_registered_clients(self, client):
        client.post("/client", json={"name": "A", "program": "Fat Loss (FL)", "weight": 70})
        client.post("/client", json={"name": "B", "program": "Muscle Gain (MG)", "weight": 80})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "A" in names
        assert "B" in names


# ---------------------------------------------------------------------------
# Route tests — POST /progress (v2.2.1: weekly adherence tracking)
# ---------------------------------------------------------------------------

class TestProgressRoute:
    def test_save_progress(self, client):
        response = client.post(
            "/progress",
            json={"client_name": "Ravi", "adherence": 85},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["client_name"] == "Ravi"
        assert data["adherence"] == 85
        assert "week" in data

    def test_missing_client_name_returns_400(self, client):
        response = client.post("/progress", json={"adherence": 50})
        assert response.status_code == 400
        assert b"client_name" in response.data

    def test_get_progress(self, client):
        client.post("/progress", json={"client_name": "Ravi", "adherence": 85})
        response = client.get("/progress/Ravi")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["client_name"] == "Ravi"
        assert data[0]["adherence"] == 85

    def test_get_progress_empty(self, client):
        response = client.get("/progress/Nobody")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_get_progress_chart(self, client):
        client.post("/progress", json={"client_name": "Ravi", "adherence": 85})
        response = client.get("/progress/chart/Ravi")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/png"

    def test_get_progress_chart_empty(self, client):
        response = client.get("/progress/chart/Nobody")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Route tests — GET /calories
# ---------------------------------------------------------------------------

class TestCaloriesRoute:
    def test_valid_request(self, client):
        response = client.get("/calories?weight=75&program=Fat Loss (FL)")
        assert response.status_code == 200
        data = response.get_json()
        assert "estimated_daily_calories" in data
        assert data["program"] == "Fat Loss (FL)"
        assert data["weight_kg"] == 75.0

    def test_unknown_program_returns_404(self, client):
        response = client.get("/calories?weight=75&program=XX")
        assert response.status_code == 404

    def test_zero_weight_returns_400(self, client):
        response = client.get("/calories?weight=0&program=Fat Loss (FL)")
        assert response.status_code == 400

    def test_negative_weight_returns_400(self, client):
        response = client.get("/calories?weight=-10&program=Fat Loss (FL)")
        assert response.status_code == 400

    def test_non_numeric_weight_returns_400(self, client):
        response = client.get("/calories?weight=abc&program=Fat Loss (FL)")
        assert response.status_code == 400

    def test_mg_program(self, client):
        response = client.get("/calories?weight=80&program=Muscle Gain (MG)")
        data = response.get_json()
        assert data["estimated_daily_calories"] == int(80 * PROGRAMS["Muscle Gain (MG)"]["factor"])
