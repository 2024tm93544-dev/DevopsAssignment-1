"""
Pytest suite for ACEest Fitness & Gym Flask API (v1).
Covers: utility functions, all four route responses, and edge-case validation.
"""

import pytest
from app import app, calculate_calories, recommend_program, PROGRAMS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
        """At the 80 kg reference, result equals the program base target."""
        assert calculate_calories(80, "FL") == PROGRAMS["FL"]["calorie_target"]

    def test_mg_reference_weight(self):
        assert calculate_calories(80, "MG") == PROGRAMS["MG"]["calorie_target"]

    def test_bg_reference_weight(self):
        assert calculate_calories(80, "BG") == PROGRAMS["BG"]["calorie_target"]

    def test_heavier_client_gets_more_calories(self):
        light = calculate_calories(60, "MG")
        heavy = calculate_calories(100, "MG")
        assert heavy > light

    def test_unknown_program_returns_none(self):
        assert calculate_calories(75, "XX") is None

    def test_result_is_integer(self):
        result = calculate_calories(70, "FL")
        assert isinstance(result, int)


class TestRecommendProgram:
    def test_fat_loss_keywords(self):
        assert recommend_program("fat loss") == "FL"
        assert recommend_program("I want to cut") == "FL"
        assert recommend_program("Weight loss goal") == "FL"

    def test_muscle_gain_keywords(self):
        assert recommend_program("muscle gain") == "MG"
        assert recommend_program("bulk up") == "MG"
        assert recommend_program("I want to gain mass") == "MG"

    def test_unknown_goal_defaults_to_beginner(self):
        assert recommend_program("general fitness") == "BG"
        assert recommend_program("stay healthy") == "BG"

    def test_case_insensitive(self):
        assert recommend_program("FAT LOSS") == "FL"
        assert recommend_program("MUSCLE GAIN") == "MG"


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
        for key in ("FL", "MG", "BG"):
            assert key in data

    def test_program_has_required_fields(self, client):
        response = client.get("/programs")
        data = response.get_json()
        for program in data.values():
            assert "name" in program
            assert "workout" in program
            assert "diet" in program


# ---------------------------------------------------------------------------
# Route tests — POST /client
# ---------------------------------------------------------------------------

class TestClientRoute:
    def test_valid_fat_loss_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Ravi", "goal": "fat loss"},
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["recommended_program"] == "FL"
        assert data["client"] == "Ravi"

    def test_valid_muscle_gain_client(self, client):
        response = client.post(
            "/client",
            json={"name": "Priya", "goal": "muscle gain"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["recommended_program"] == "MG"

    def test_missing_name_returns_400(self, client):
        response = client.post("/client", json={"goal": "fat loss"})
        assert response.status_code == 400
        assert b"name" in response.data

    def test_missing_goal_returns_400(self, client):
        response = client.post("/client", json={"name": "Anjali"})
        assert response.status_code == 400
        assert b"goal" in response.data

    def test_response_includes_workout_and_diet(self, client):
        response = client.post(
            "/client",
            json={"name": "Kumar", "goal": "bulk up"},
        )
        data = response.get_json()
        assert "workout" in data
        assert "diet" in data


# ---------------------------------------------------------------------------
# Route tests — GET /calories
# ---------------------------------------------------------------------------

class TestCaloriesRoute:
    def test_valid_request(self, client):
        response = client.get("/calories?weight=75&program=FL")
        assert response.status_code == 200
        data = response.get_json()
        assert "estimated_daily_calories" in data
        assert data["program"] == "FL"
        assert data["weight_kg"] == 75.0

    def test_unknown_program_returns_404(self, client):
        response = client.get("/calories?weight=75&program=XX")
        assert response.status_code == 404

    def test_zero_weight_returns_400(self, client):
        response = client.get("/calories?weight=0&program=FL")
        assert response.status_code == 400

    def test_negative_weight_returns_400(self, client):
        response = client.get("/calories?weight=-10&program=FL")
        assert response.status_code == 400

    def test_non_numeric_weight_returns_400(self, client):
        response = client.get("/calories?weight=abc&program=FL")
        assert response.status_code == 400

    def test_mg_program(self, client):
        response = client.get("/calories?weight=80&program=MG")
        data = response.get_json()
        assert data["estimated_daily_calories"] == PROGRAMS["MG"]["calorie_target"]
