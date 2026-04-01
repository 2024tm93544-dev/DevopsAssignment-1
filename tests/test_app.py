"""
Pytest suite for ACEest Fitness & Gym Flask API (v1.1.2).
Covers: utility functions, all route responses, client management,
CSV export, chart data, and edge-case validation.
"""

import pytest
from app import app, calculate_calories, recommend_program, PROGRAMS, clients


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def clear_clients():
    """Reset the in-memory client store between tests."""
    clients.clear()
    yield
    clients.clear()


# ---------------------------------------------------------------------------
# Unit tests — pure logic
# ---------------------------------------------------------------------------

class TestCalculateCalories:
    def test_fl_reference_weight(self):
        """At the 80 kg reference, check against calorie factor."""
        assert calculate_calories(80, "FL") == int(80 * PROGRAMS["FL"]["calorie_factor"])

    def test_mg_reference_weight(self):
        assert calculate_calories(80, "MG") == int(80 * PROGRAMS["MG"]["calorie_factor"])

    def test_bg_reference_weight(self):
        assert calculate_calories(80, "BG") == int(80 * PROGRAMS["BG"]["calorie_factor"])

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
# Route tests — POST /client (v1.1.2: now accepts notes & adherence)
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

    def test_client_with_notes_and_adherence(self, client):
        """v1.1.2 feature: coach notes and weekly adherence tracking."""
        response = client.post(
            "/client",
            json={
                "name": "Karthik",
                "goal": "fat loss",
                "age": 28,
                "weight": 82,
                "adherence": 75,
                "notes": "Focus on consistency",
            },
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["adherence"] == 75
        assert data["notes"] == "Focus on consistency"

    def test_client_stored_in_list(self, client):
        """v1.1.2 feature: clients are persisted in the in-memory list."""
        client.post("/client", json={"name": "Meena", "goal": "bulk up"})
        assert len(clients) == 1
        assert clients[0]["name"] == "Meena"

    def test_default_adherence_is_zero(self, client):
        """When adherence is omitted it should default to 0."""
        response = client.post(
            "/client",
            json={"name": "Deepa", "goal": "general fitness"},
        )
        data = response.get_json()
        assert data["adherence"] == 0


# ---------------------------------------------------------------------------
# Route tests — GET /clients (v1.1.2: multi-client list)
# ---------------------------------------------------------------------------

class TestClientsListRoute:
    def test_empty_list(self, client):
        response = client.get("/clients")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_lists_registered_clients(self, client):
        client.post("/client", json={"name": "A", "goal": "fat loss"})
        client.post("/client", json={"name": "B", "goal": "muscle gain"})
        response = client.get("/clients")
        data = response.get_json()
        assert len(data) == 2
        assert data[0]["name"] == "A"
        assert data[1]["name"] == "B"


# ---------------------------------------------------------------------------
# Route tests — GET /clients/export (v1.1.2: CSV export)
# ---------------------------------------------------------------------------

class TestExportCSV:
    def test_export_empty_returns_404(self, client):
        response = client.get("/clients/export")
        assert response.status_code == 404

    def test_export_csv_content(self, client):
        client.post("/client", json={
            "name": "Ravi", "goal": "fat loss",
            "age": 30, "weight": 75, "adherence": 80, "notes": "Good progress",
        })
        response = client.get("/clients/export")
        assert response.status_code == 200
        assert response.content_type == "text/csv; charset=utf-8"
        text = response.data.decode()
        assert "Name" in text
        assert "Ravi" in text


# ---------------------------------------------------------------------------
# Route tests — GET /clients/chart-data (v1.1.2: progress chart)
# ---------------------------------------------------------------------------

class TestChartData:
    def test_empty_chart_data(self, client):
        response = client.get("/clients/chart-data")
        data = response.get_json()
        assert data["names"] == []
        assert data["adherence"] == []

    def test_chart_data_after_registration(self, client):
        client.post("/client", json={
            "name": "Vimal", "goal": "muscle gain", "adherence": 90,
        })
        response = client.get("/clients/chart-data")
        data = response.get_json()
        assert data["names"] == ["Vimal"]
        assert data["adherence"] == [90]


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
        assert data["estimated_daily_calories"] == int(80 * PROGRAMS["MG"]["calorie_factor"])
