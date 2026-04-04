"""
Pytest suite for ACEest Fitness & Gym Flask API (v3.0.1).
Covers: utility functions, all route responses, client management
with SQLite persistence, progress tracking, workout logging, metrics, BMI,
and edge-case validation.
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
        assert calculate_calories(80, "Fat Loss (FL) – 3 day") == int(80 * PROGRAMS["Fat Loss (FL) – 3 day"]["factor"])

    def test_mg_reference_weight(self):
        assert calculate_calories(80, "Muscle Gain (MG) – PPL") == int(80 * PROGRAMS["Muscle Gain (MG) – PPL"]["factor"])

    def test_bg_reference_weight(self):
        assert calculate_calories(80, "Beginner (BG)") == int(80 * PROGRAMS["Beginner (BG)"]["factor"])

    def test_heavier_client_gets_more_calories(self):
        light = calculate_calories(60, "Muscle Gain (MG) – PPL")
        heavy = calculate_calories(100, "Muscle Gain (MG) – PPL")
        assert heavy > light

    def test_unknown_program_returns_none(self):
        assert calculate_calories(75, "XX") is None

    def test_result_is_integer(self):
        result = calculate_calories(70, "Fat Loss (FL) – 3 day")
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
            assert key.encode("utf-8") in response.data

    def test_version_in_page(self, client):
        response = client.get("/")
        assert b"v3.0.1" in response.data


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
        for key in ("Fat Loss (FL) – 3 day", "Muscle Gain (MG) – PPL", "Beginner (BG)"):
            assert key in data

    def test_program_has_factor_field(self, client):
        response = client.get("/programs")
        data = response.get_json()
        for program in data.values():
            assert "factor" in program


# ---------------------------------------------------------------------------
# Route tests — POST /client (v3.0.1 updates)
# ---------------------------------------------------------------------------

class TestClientRoute:
    def test_valid_fat_loss_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Ravi", "program": "Fat Loss (FL) – 3 day", "age": 30, "height": 175, "weight": 75, "target_weight": 70, "target_adherence": 80},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["program"] == "Fat Loss (FL) – 3 day"
        assert data["client"] == "Ravi"
        assert data["height_cm"] == 175
        assert data["target_weight"] == 70
        assert data["calories"] == int(75 * PROGRAMS["Fat Loss (FL) – 3 day"]["factor"])

    def test_valid_muscle_gain_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Priya", "program": "Muscle Gain (MG) – PPL", "weight": 65},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["program"] == "Muscle Gain (MG) – PPL"

    def test_missing_name_returns_400(self, client):
        response = client.post("/client", json={"program": "Fat Loss (FL) – 3 day"})
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
            json={"name": "Kumar", "program": "Muscle Gain (MG) – PPL", "weight": 80},
        )
        data = response.get_json()
        assert "calories" in data
        assert data["calories"] == int(80 * PROGRAMS["Muscle Gain (MG) – PPL"]["factor"])

    def test_client_stored_in_db(self, client):
        client.post("/client", json={"name": "Meena", "program": "Beginner (BG)", "weight": 60})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Meena"

    def test_upsert_replaces_existing(self, client):
        client.post("/client", json={"name": "Ravi", "program": "Fat Loss (FL) – 3 day", "weight": 75})
        client.post("/client", json={"name": "Ravi", "program": "Muscle Gain (MG) – PPL", "weight": 80})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["program"] == "Muscle Gain (MG) – PPL"


# ---------------------------------------------------------------------------
# Route tests — GET /client/<name>
# ---------------------------------------------------------------------------

class TestLoadClient:
    def test_load_existing_client(self, client):
        client.post("/client", json={
            "name": "Ravi", "program": "Fat Loss (FL) – 3 day", "age": 30, "weight": 75, "height": 180
        })
        response = client.get("/client/Ravi")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Ravi"
        assert data["age"] == 30
        assert data["height"] == 180
        assert data["calories"] == int(75 * PROGRAMS["Fat Loss (FL) – 3 day"]["factor"])

    def test_load_missing_client(self, client):
        response = client.get("/client/Nobody")
        assert response.status_code == 404
        assert b"not found" in response.data


# ---------------------------------------------------------------------------
# Route tests — GET /clients
# ---------------------------------------------------------------------------

class TestClientsListRoute:
    def test_empty_list(self, client):
        response = client.get("/clients")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_registered_clients(self, client):
        client.post("/client", json={"name": "A", "program": "Fat Loss (FL) – 3 day", "weight": 70})
        client.post("/client", json={"name": "B", "program": "Muscle Gain (MG) – PPL", "weight": 80})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "A" in names
        assert "B" in names


# ---------------------------------------------------------------------------
# Route tests — POST /progress
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


# ---------------------------------------------------------------------------
# Route tests — GET /calories
# ---------------------------------------------------------------------------

class TestCaloriesRoute:
    def test_valid_request(self, client):
        response = client.get("/calories?weight=75&program=Fat Loss (FL) – 3 day")
        assert response.status_code == 200
        data = response.get_json()
        assert "estimated_daily_calories" in data
        assert data["program"] == "Fat Loss (FL) – 3 day"
        assert data["weight_kg"] == 75.0

    def test_unknown_program_returns_404(self, client):
        response = client.get("/calories?weight=75&program=XX")
        assert response.status_code == 404

    def test_zero_weight_returns_400(self, client):
        response = client.get("/calories?weight=0&program=Fat Loss (FL) – 3 day")
        assert response.status_code == 400

    def test_negative_weight_returns_400(self, client):
        response = client.get("/calories?weight=-10&program=Fat Loss (FL) – 3 day")
        assert response.status_code == 400

    def test_mg_program(self, client):
        response = client.get("/calories?weight=80&program=Muscle Gain (MG) – PPL")
        data = response.get_json()
        assert data["estimated_daily_calories"] == int(80 * PROGRAMS["Muscle Gain (MG) – PPL"]["factor"])


# ---------------------------------------------------------------------------
# Route tests — Workouts & Metrics & BMI
# ---------------------------------------------------------------------------

class TestV3Features:
    def test_log_workout(self, client):
        client.post("/client", json={"name": "Ravi", "program": "Fat Loss (FL) – 3 day"})
        response = client.post("/workouts", json={
            "client_name": "Ravi",
            "workout_type": "Strength",
            "duration_min": 45,
            "exercise_name": "Bench Press",
            "sets": 3,
            "reps": 10,
            "exercise_weight": 60
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "workout_id" in data

        history = client.get("/workouts/Ravi")
        assert len(history.get_json()) == 1
        assert history.get_json()[0]["workout_type"] == "Strength"

    def test_log_metrics(self, client):
        client.post("/client", json={"name": "Ravi", "program": "Fat Loss (FL) – 3 day"})
        response = client.post("/metrics", json={
            "client_name": "Ravi",
            "weight": 76,
            "bodyfat": 15
        })
        assert response.status_code == 201

        # Should update client weight implicitly
        c_response = client.get("/client/Ravi")
        assert c_response.get_json()["weight"] == 76

        history = client.get("/metrics/Ravi")
        assert len(history.get_json()) == 1
        assert history.get_json()[0]["weight"] == 76

    def test_metrics_chart(self, client):
        client.post("/metrics", json={"client_name": "Ravi", "weight": 76})
        response = client.get("/metrics/chart/Ravi")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/png"

    def test_bmi_calculator(self, client):
        response = client.get("/bmi?height=180&weight=80")
        assert response.status_code == 200
        data = response.get_json()
        assert "bmi" in data
        assert data["bmi"] == round(80 / (1.8 * 1.8), 1)