"""
ACEest Fitness & Gym Management Service — Test Suite v2.2.4
============================================================
Covers:
  - Utility functions  : calculate_calories, calculate_bmi
  - Programs           : GET /programs
  - Index              : GET /
  - Client CRUD        : POST /client, GET /client/<n>, GET /clients
  - Progress           : POST /progress, GET /progress/<n>, GET /progress/chart/<n>
  - Calories           : GET /calories
  - Workout logging    : POST /workout, GET /workout/<n>         [NEW v2.2.4]
  - Body metrics       : POST /metrics, GET /metrics/<n>         [NEW v2.2.4]
  - Weight trend chart : GET /metrics/chart/<n>                  [NEW v2.2.4]
  - BMI info           : GET /bmi/<n>                            [NEW v2.2.4]
"""

import os
import tempfile
import pytest

# Import app after fixture sets up the temp DB per test
import app as app_module
from app import app, calculate_calories, calculate_bmi, PROGRAMS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Flask test client with a fresh isolated SQLite file per test.

    Uses a real temp file (not :memory:) so all get_db() connections within
    a test share the same on-disk state.
    """
    app.config["TESTING"] = True

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name

    app_module.DB_NAME = tmp_path
    app_module.init_db()

    with app.test_client() as c:
        yield c

    os.unlink(tmp_path)


def register(client, **kwargs):
    """Helper: register a client with sensible defaults."""
    payload = {
        "name": "TestUser",
        "age": 28,
        "height": 175.0,
        "weight": 75.0,
        "program": "Fat Loss (FL) – 3 day",
        "target_weight": 68.0,
        "target_adherence": 85,
    }
    payload.update(kwargs)
    return client.post("/client", json=payload)


# ===========================================================================
# 1. Utility — calculate_calories
# ===========================================================================

class TestCalculateCalories:
    def test_fat_loss_3day(self):
        assert calculate_calories(75, "Fat Loss (FL) – 3 day") == 75 * 22

    def test_fat_loss_5day(self):
        assert calculate_calories(80, "Fat Loss (FL) – 5 day") == 80 * 24

    def test_muscle_gain_ppl(self):
        assert calculate_calories(90, "Muscle Gain (MG) – PPL") == 90 * 35

    def test_beginner(self):
        assert calculate_calories(60, "Beginner (BG)") == 60 * 26

    def test_unknown_program_returns_none(self):
        assert calculate_calories(70, "Fat Loss (FL)") is None  # old v2.2.1 key

    def test_zero_weight(self):
        assert calculate_calories(0, "Beginner (BG)") == 0

    def test_fractional_weight(self):
        result = calculate_calories(72.5, "Beginner (BG)")
        assert result == int(72.5 * 26)


# ===========================================================================
# 2. Utility — calculate_bmi
# ===========================================================================

class TestCalculateBmi:
    def test_normal_bmi(self):
        result = calculate_bmi(70, 175)
        assert result is not None
        assert result["bmi"] == round(70 / (1.75 ** 2), 1)
        assert result["category"] == "Normal"

    def test_underweight(self):
        result = calculate_bmi(45, 175)
        assert result["category"] == "Underweight"

    def test_overweight(self):
        result = calculate_bmi(85, 170)
        assert result["category"] == "Overweight"

    def test_obese(self):
        result = calculate_bmi(120, 170)
        assert result["category"] == "Obese"

    def test_zero_height_returns_none(self):
        assert calculate_bmi(70, 0) is None

    def test_zero_weight_returns_none(self):
        assert calculate_bmi(0, 175) is None

    def test_none_inputs_return_none(self):
        assert calculate_bmi(None, 175) is None
        assert calculate_bmi(70, None) is None

    def test_risk_field_present(self):
        result = calculate_bmi(70, 175)
        assert "risk" in result
        assert len(result["risk"]) > 0


# ===========================================================================
# 3. GET /programs
# ===========================================================================

class TestPrograms:
    def test_returns_200(self, client):
        r = client.get("/programs")
        assert r.status_code == 200

    def test_all_four_programs_present(self, client):
        data = client.get("/programs").get_json()
        assert "Fat Loss (FL) – 3 day" in data
        assert "Fat Loss (FL) – 5 day" in data
        assert "Muscle Gain (MG) – PPL" in data
        assert "Beginner (BG)" in data

    def test_each_program_has_factor_and_desc(self, client):
        data = client.get("/programs").get_json()
        for key, prog in data.items():
            assert "factor" in prog, f"Missing factor in {key}"
            assert "desc" in prog, f"Missing desc in {key}"

    def test_old_v221_keys_absent(self, client):
        data = client.get("/programs").get_json()
        assert "Fat Loss (FL)" not in data
        assert "Muscle Gain (MG)" not in data


# ===========================================================================
# 4. GET /
# ===========================================================================

class TestIndex:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_html_contains_v224(self, client):
        r = client.get("/")
        assert b"v2.2.4" in r.data

    def test_html_lists_programs(self, client):
        r = client.get("/")
        assert b"Fat Loss" in r.data
        assert b"Beginner" in r.data


# ===========================================================================
# 5. POST /client  and  GET /client/<n>
# ===========================================================================

class TestClientRegistration:
    def test_register_returns_201(self, client):
        r = register(client)
        assert r.status_code == 201

    def test_register_response_fields(self, client):
        data = register(client).get_json()
        assert data["client"] == "TestUser"
        assert data["calories"] == int(75.0 * 22)
        assert data["height_cm"] == 175.0
        assert data["target_weight_kg"] == 68.0
        assert data["target_adherence_pct"] == 85

    def test_register_missing_name(self, client):
        r = client.post("/client", json={"program": "Beginner (BG)"})
        assert r.status_code == 400
        assert "name" in r.get_json()["error"]

    def test_register_missing_program(self, client):
        r = client.post("/client", json={"name": "NoProgram"})
        assert r.status_code == 400
        assert "program" in r.get_json()["error"]

    def test_register_unknown_program(self, client):
        r = client.post("/client", json={"name": "A", "program": "Unknown"})
        assert r.status_code == 400

    def test_register_upsert(self, client):
        register(client, weight=75.0)
        r2 = register(client, weight=80.0)
        assert r2.status_code == 201
        assert r2.get_json()["weight_kg"] == 80.0

    def test_load_client(self, client):
        register(client)
        r = client.get("/client/TestUser")
        assert r.status_code == 200
        data = r.get_json()
        assert data["name"] == "TestUser"
        assert data["height"] == 175.0
        assert data["target_weight"] == 68.0
        assert data["target_adherence"] == 85

    def test_load_nonexistent_client(self, client):
        r = client.get("/client/Ghost")
        assert r.status_code == 404

    def test_list_clients_empty(self, client):
        r = client.get("/clients")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_list_clients_after_register(self, client):
        register(client)
        data = client.get("/clients").get_json()
        assert len(data) == 1
        assert data[0]["name"] == "TestUser"


# ===========================================================================
# 6. POST /progress  and  GET /progress/<n>
# ===========================================================================

class TestProgress:
    def test_save_progress_returns_201(self, client):
        r = client.post("/progress", json={"client_name": "TestUser", "adherence": 80})
        assert r.status_code == 201

    def test_save_progress_response(self, client):
        data = client.post(
            "/progress", json={"client_name": "TestUser", "adherence": 75}
        ).get_json()
        assert data["client_name"] == "TestUser"
        assert data["adherence"] == 75
        assert "week" in data

    def test_save_progress_missing_client_name(self, client):
        r = client.post("/progress", json={"adherence": 90})
        assert r.status_code == 400

    def test_get_progress_empty(self, client):
        r = client.get("/progress/Nobody")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_progress_after_save(self, client):
        client.post("/progress", json={"client_name": "TestUser", "adherence": 70})
        client.post("/progress", json={"client_name": "TestUser", "adherence": 90})
        data = client.get("/progress/TestUser").get_json()
        assert len(data) == 2
        adherences = [d["adherence"] for d in data]
        assert 70 in adherences
        assert 90 in adherences


# ===========================================================================
# 7. GET /progress/chart/<n>
# ===========================================================================

class TestProgressChart:
    def test_chart_no_data_returns_404(self, client):
        r = client.get("/progress/chart/Nobody")
        assert r.status_code == 404

    def test_chart_returns_png(self, client):
        client.post("/progress", json={"client_name": "ChartUser", "adherence": 80})
        r = client.get("/progress/chart/ChartUser")
        assert r.status_code == 200
        assert r.content_type == "image/png"
        assert len(r.data) > 0


# ===========================================================================
# 8. GET /calories
# ===========================================================================

class TestCaloriesEndpoint:
    def test_valid_request(self, client):
        r = client.get("/calories?weight=80&program=Beginner (BG)")
        assert r.status_code == 200
        data = r.get_json()
        assert data["estimated_daily_calories"] == int(80 * 26)

    def test_fat_loss_5day(self, client):
        r = client.get("/calories?weight=70&program=Fat Loss (FL) – 5 day")
        assert r.status_code == 200
        assert r.get_json()["estimated_daily_calories"] == int(70 * 24)

    def test_missing_weight(self, client):
        r = client.get("/calories?program=Beginner (BG)")
        assert r.status_code == 400

    def test_invalid_weight(self, client):
        r = client.get("/calories?weight=abc&program=Beginner (BG)")
        assert r.status_code == 400

    def test_unknown_program(self, client):
        r = client.get("/calories?weight=70&program=NonExistent")
        assert r.status_code == 404

    def test_negative_weight(self, client):
        r = client.get("/calories?weight=-10&program=Beginner (BG)")
        assert r.status_code == 400


# ===========================================================================
# 9. POST /workout  and  GET /workout/<n>              [NEW v2.2.4]
# ===========================================================================

class TestWorkout:
    WORKOUT_PAYLOAD = {
        "client_name": "WorkoutUser",
        "date": "2025-04-01",
        "workout_type": "Strength",
        "duration_min": 60,
        "notes": "Felt strong today",
        "exercises": [
            {"name": "Bench Press", "sets": 4, "reps": 8, "weight": 80.0},
            {"name": "Squat", "sets": 4, "reps": 6, "weight": 100.0},
        ],
    }

    def test_log_workout_returns_201(self, client):
        r = client.post("/workout", json=self.WORKOUT_PAYLOAD)
        assert r.status_code == 201

    def test_log_workout_response_fields(self, client):
        data = client.post("/workout", json=self.WORKOUT_PAYLOAD).get_json()
        assert data["client_name"] == "WorkoutUser"
        assert data["workout_type"] == "Strength"
        assert data["duration_min"] == 60
        assert "Bench Press" in data["exercises_saved"]
        assert "Squat" in data["exercises_saved"]
        assert "workout_id" in data

    def test_log_workout_missing_client_name(self, client):
        r = client.post("/workout", json={"workout_type": "Strength"})
        assert r.status_code == 400

    def test_log_workout_invalid_type(self, client):
        r = client.post("/workout", json={
            "client_name": "WorkoutUser",
            "workout_type": "InvalidType",
        })
        assert r.status_code == 400

    def test_log_workout_no_exercises(self, client):
        r = client.post("/workout", json={
            "client_name": "WorkoutUser",
            "workout_type": "Mobility",
            "duration_min": 30,
        })
        assert r.status_code == 201
        assert r.get_json()["exercises_saved"] == []

    def test_get_workouts_empty(self, client):
        r = client.get("/workout/NoOne")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_workouts_returns_history(self, client):
        client.post("/workout", json=self.WORKOUT_PAYLOAD)
        data = client.get("/workout/WorkoutUser").get_json()
        assert len(data) == 1
        assert data[0]["workout_type"] == "Strength"
        assert len(data[0]["exercises"]) == 2

    def test_get_workouts_exercises_fields(self, client):
        client.post("/workout", json=self.WORKOUT_PAYLOAD)
        exercises = client.get("/workout/WorkoutUser").get_json()[0]["exercises"]
        names = [e["name"] for e in exercises]
        assert "Bench Press" in names
        assert "Squat" in names

    def test_get_workouts_multiple_sessions(self, client):
        client.post("/workout", json={**self.WORKOUT_PAYLOAD, "date": "2025-04-01"})
        client.post("/workout", json={**self.WORKOUT_PAYLOAD, "date": "2025-04-08"})
        data = client.get("/workout/WorkoutUser").get_json()
        assert len(data) == 2

    def test_valid_workout_types(self, client):
        for wtype in ["Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"]:
            r = client.post("/workout", json={
                "client_name": "WorkoutUser",
                "workout_type": wtype,
            })
            assert r.status_code == 201, f"Failed for workout_type={wtype}"


# ===========================================================================
# 10. POST /metrics  and  GET /metrics/<n>             [NEW v2.2.4]
# ===========================================================================

class TestMetrics:
    METRICS_PAYLOAD = {
        "client_name": "MetricsUser",
        "date": "2025-04-01",
        "weight": 74.5,
        "waist": 82.0,
        "bodyfat": 18.2,
    }

    def test_log_metrics_returns_201(self, client):
        r = client.post("/metrics", json=self.METRICS_PAYLOAD)
        assert r.status_code == 201

    def test_log_metrics_response_fields(self, client):
        data = client.post("/metrics", json=self.METRICS_PAYLOAD).get_json()
        assert data["client_name"] == "MetricsUser"
        assert data["weight_kg"] == 74.5
        assert data["waist_cm"] == 82.0
        assert data["bodyfat_pct"] == 18.2
        assert data["date"] == "2025-04-01"

    def test_log_metrics_missing_client_name(self, client):
        r = client.post("/metrics", json={"date": "2025-04-01", "weight": 70})
        assert r.status_code == 400

    def test_log_metrics_partial_fields_allowed(self, client):
        # weight only — waist and bodyfat can be null
        r = client.post("/metrics", json={
            "client_name": "MetricsUser",
            "date": "2025-04-01",
            "weight": 74.5,
        })
        assert r.status_code == 201

    def test_get_metrics_empty(self, client):
        r = client.get("/metrics/NoOne")
        assert r.status_code == 200
        assert r.get_json() == []

    def test_get_metrics_returns_entries(self, client):
        client.post("/metrics", json=self.METRICS_PAYLOAD)
        data = client.get("/metrics/MetricsUser").get_json()
        assert len(data) == 1
        assert data[0]["weight"] == 74.5

    def test_get_metrics_multiple_entries(self, client):
        client.post("/metrics", json={**self.METRICS_PAYLOAD, "date": "2025-04-01", "weight": 74.5})
        client.post("/metrics", json={**self.METRICS_PAYLOAD, "date": "2025-04-08", "weight": 74.0})
        data = client.get("/metrics/MetricsUser").get_json()
        assert len(data) == 2

    def test_get_metrics_ordered_by_date_desc(self, client):
        client.post("/metrics", json={**self.METRICS_PAYLOAD, "date": "2025-04-01"})
        client.post("/metrics", json={**self.METRICS_PAYLOAD, "date": "2025-04-08"})
        data = client.get("/metrics/MetricsUser").get_json()
        assert data[0]["date"] == "2025-04-08"  # most recent first


# ===========================================================================
# 11. GET /metrics/chart/<n>                           [NEW v2.2.4]
# ===========================================================================

class TestWeightTrendChart:
    def test_no_data_returns_404(self, client):
        r = client.get("/metrics/chart/Nobody")
        assert r.status_code == 404

    def test_returns_png(self, client):
        client.post("/metrics", json={
            "client_name": "ChartUser",
            "date": "2025-04-01",
            "weight": 74.5,
        })
        r = client.get("/metrics/chart/ChartUser")
        assert r.status_code == 200
        assert r.content_type == "image/png"
        assert len(r.data) > 0

    def test_client_with_null_weight_excluded(self, client):
        # Only null weight entries — should 404
        client.post("/metrics", json={
            "client_name": "NullWeightUser",
            "date": "2025-04-01",
            "waist": 80.0,
        })
        r = client.get("/metrics/chart/NullWeightUser")
        assert r.status_code == 404


# ===========================================================================
# 12. GET /bmi/<n>                                     [NEW v2.2.4]
# ===========================================================================

class TestBmi:
    def test_bmi_for_registered_client(self, client):
        register(client, weight=70.0, height=175.0)
        r = client.get("/bmi/TestUser")
        assert r.status_code == 200
        data = r.get_json()
        assert data["client"] == "TestUser"
        assert "bmi" in data
        assert "category" in data
        assert "risk" in data

    def test_bmi_correct_value(self, client):
        register(client, weight=70.0, height=175.0)
        data = client.get("/bmi/TestUser").get_json()
        expected_bmi = round(70.0 / (1.75 ** 2), 1)
        assert data["bmi"] == expected_bmi

    def test_bmi_nonexistent_client(self, client):
        r = client.get("/bmi/Ghost")
        assert r.status_code == 404

    def test_bmi_missing_height_returns_400(self, client):
        # Register without height
        client.post("/client", json={
            "name": "NoHeight",
            "program": "Beginner (BG)",
            "weight": 70.0,
        })
        r = client.get("/bmi/NoHeight")
        assert r.status_code == 400

    def test_bmi_categories(self, client):
        cases = [
            (45.0, 175.0, "Underweight"),
            (70.0, 175.0, "Normal"),
            (85.0, 170.0, "Overweight"),
            (120.0, 170.0, "Obese"),
        ]
        for i, (weight, height, expected_category) in enumerate(cases):
            name = f"BmiUser{i}"
            client.post("/client", json={
                "name": name,
                "program": "Beginner (BG)",
                "weight": weight,
                "height": height,
            })
            data = client.get(f"/bmi/{name}").get_json()
            assert data["category"] == expected_category, (
                f"Expected {expected_category} for weight={weight}, height={height}, "
                f"got {data['category']}"
            )