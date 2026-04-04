from flask import Flask, jsonify, request, render_template_string, Response
import sqlite3
import os
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, date

app = Flask(__name__)

DB_NAME = os.environ.get("ACEEST_DB", "aceest_fitness.db")

# Core data store — updated to ACEest v2.2.4
# New programs: Fat Loss split into 3-day and 5-day; Muscle Gain renamed to PPL variant
PROGRAMS = {
    "Fat Loss (FL) – 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) – 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) – PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}


# ---------------------------------------------------------------------------
# Database helpers (mirrors v2.2.4 init_db)
# ---------------------------------------------------------------------------

def get_db():
    """Return a new SQLite connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables. Migrates clients table if schema is outdated (v2.2.1 → v2.2.4)."""
    conn = get_db()
    cur = conn.cursor()

    # --- clients table: migrate if old schema is missing new columns ---
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("PRAGMA table_info(clients)")
        cols = {row[1] for row in cur.fetchall()}
        required = {
            "id", "name", "age", "height", "weight",
            "program", "calories", "target_weight", "target_adherence",
        }
        if not required.issubset(cols):
            cur.execute("DROP TABLE clients")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            height REAL,
            weight REAL,
            program TEXT,
            calories INTEGER,
            target_weight REAL,
            target_adherence INTEGER
        )
    """)

    # --- progress table (unchanged from v2.2.1) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
        )
    """)

    # --- workouts table (NEW in v2.2.4) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
    """)

    # --- exercises table (NEW in v2.2.4) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    """)

    # --- metrics table (NEW in v2.2.4) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            date TEXT,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def calculate_calories(weight_kg, program_key):
    """Return estimated daily calorie target.

    Uses the program's factor multiplied by body weight.
    Returns None for unknown programs.
    """
    if program_key not in PROGRAMS:
        return None
    factor = PROGRAMS[program_key]["factor"]
    return int(weight_kg * factor)


def calculate_bmi(weight_kg, height_cm):
    """Return (bmi, category, risk) tuple. Returns None if inputs invalid."""
    if not weight_kg or not height_cm or height_cm <= 0 or weight_kg <= 0:
        return None
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)

    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category, risk = "Normal", "Low risk if active and strong."
    elif bmi < 30:
        category, risk = "Overweight", "Moderate risk; focus on adherence and progressive activity."
    else:
        category, risk = "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."

    return {"bmi": bmi, "category": category, "risk": risk}


# ---------------------------------------------------------------------------
# HTML template (updated for v2.2.4)
# ---------------------------------------------------------------------------

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ACEest Fitness & Gym</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; margin: 0; }
        header { background: #d4af37; padding: 20px; text-align: center; }
        header h1 { color: #000; margin: 0; }
        main { padding: 30px; }
        .programs { display: flex; gap: 20px; flex-wrap: wrap; }
        .card { background: #2b2b2b; border-radius: 8px; padding: 20px; min-width: 240px; flex: 1; }
        .card h2 { color: #d4af37; }
        .card p { color: #ccc; margin: 4px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #d4af37; }
    </style>
</head>
<body>
    <header><h1>ACEest Functional Fitness System v2.2.4</h1></header>
    <main>
        <h2>Available Programs</h2>
        <div class="programs">
            {% for key, p in programs.items() %}
            <div class="card">
                <h2>{{ key }}</h2>
                <p>Calorie Factor: {{ p.factor }} kcal/kg</p>
                <p style="color:#aaa; font-size:0.9em;">{{ p.desc }}</p>
            </div>
            {% endfor %}
        </div>
        {% if clients %}
        <h2>Client List</h2>
        <table>
            <tr>
                <th>Name</th><th>Age</th><th>Height (cm)</th><th>Weight (kg)</th>
                <th>Program</th><th>Calories</th><th>Target Weight</th><th>Target Adherence</th>
            </tr>
            {% for c in clients %}
            <tr>
                <td>{{ c.name }}</td>
                <td>{{ c.age or '-' }}</td>
                <td>{{ c.height or '-' }}</td>
                <td>{{ c.weight or '-' }}</td>
                <td>{{ c.program }}</td>
                <td>{{ c.calories or '-' }} kcal/day</td>
                <td>{{ c.target_weight or '-' }} kg</td>
                <td>{{ c.target_adherence or '-' }}%</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
    </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes — existing (updated)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, age, height, weight, program, calories, target_weight, target_adherence FROM clients"
    ).fetchall()
    conn.close()
    return render_template_string(INDEX_HTML, programs=PROGRAMS, clients=[dict(r) for r in rows])


@app.route("/programs")
def get_programs():
    return jsonify(PROGRAMS)


@app.route("/client", methods=["POST"])
def register_client():
    """Register or update a client (v2.2.4: adds height, target_weight, target_adherence)."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    program_key = data.get("program", "").strip()
    target_weight = data.get("target_weight")
    target_adherence = data.get("target_adherence")

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not program_key:
        return jsonify({"error": "program is required"}), 400
    if program_key not in PROGRAMS:
        return jsonify({"error": f"unknown program '{program_key}'"}), 400

    calories = calculate_calories(weight if weight else 0, program_key)

    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO clients
        (name, age, height, weight, program, calories, target_weight, target_adherence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, height, weight, program_key, calories, target_weight, target_adherence))
    conn.commit()
    conn.close()

    return jsonify({
        "client": name,
        "age": age,
        "height_cm": height,
        "weight_kg": weight,
        "program": program_key,
        "calories": calories,
        "target_weight_kg": target_weight,
        "target_adherence_pct": target_adherence,
    }), 201


@app.route("/client/<name>")
def load_client(name):
    """Load a single client by name (v2.2.4: includes new fields)."""
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{name}' not found"}), 404

    return jsonify(dict(row))


@app.route("/clients")
def list_clients():
    """Return the full client list as JSON."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/progress", methods=["POST"])
def save_progress():
    """Save weekly adherence for a client."""
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    adherence = data.get("adherence", 0)

    if not client_name:
        return jsonify({"error": "client_name is required"}), 400

    week = datetime.now().strftime("Week %U - %Y")

    conn = get_db()
    conn.execute("""
        INSERT INTO progress (client_name, week, adherence)
        VALUES (?, ?, ?)
    """, (client_name, week, adherence))
    conn.commit()
    conn.close()

    return jsonify({"client_name": client_name, "week": week, "adherence": adherence}), 201


@app.route("/progress/<client_name>")
def get_progress(client_name):
    """Return all progress entries for a given client."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE client_name=?", (client_name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/progress/chart/<client_name>")
def progress_chart(client_name):
    """Return a weekly adherence chart PNG (mirrors v2.2.4 show_progress_chart)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
        (client_name,)
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": f"No progress data for client '{client_name}'"}), 404

    weeks = [r["week"] for r in rows]
    adherence = [r["adherence"] for r in rows]

    plt.figure(figsize=(8, 4))
    plt.plot(weeks, adherence, marker="o", linewidth=2)
    plt.title(f"Weekly Adherence – {client_name}")
    plt.xlabel("Week")
    plt.ylabel("Adherence (%)")
    plt.ylim(0, 100)
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return Response(buf.getvalue(), mimetype="image/png")


@app.route("/calories")
def calories():
    try:
        weight = float(request.args.get("weight", 0))
    except ValueError:
        return jsonify({"error": "weight must be a number"}), 400

    program_key = request.args.get("program", "")

    if weight <= 0:
        return jsonify({"error": "weight must be a positive number"}), 400

    result = calculate_calories(weight, program_key)
    if result is None:
        return jsonify({"error": f"unknown program '{program_key}'"}), 404

    return jsonify({
        "weight_kg": weight,
        "program": program_key,
        "estimated_daily_calories": result,
    })


# ---------------------------------------------------------------------------
# Routes — NEW in v2.2.4
# ---------------------------------------------------------------------------

@app.route("/workout", methods=["POST"])
def log_workout():
    """Log a workout session with optional exercises (mirrors v2.2.4 open_log_workout_window)."""
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    workout_date = data.get("date", date.today().isoformat())
    workout_type = data.get("workout_type", "").strip()
    duration_min = data.get("duration_min", 60)
    notes = data.get("notes", "")
    exercises = data.get("exercises", [])  # list of {name, sets, reps, weight}

    if not client_name:
        return jsonify({"error": "client_name is required"}), 400

    valid_types = ["Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"]
    if workout_type and workout_type not in valid_types:
        return jsonify({"error": f"workout_type must be one of {valid_types}"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (client_name, workout_date, workout_type, duration_min, notes))
    workout_id = cur.lastrowid

    saved_exercises = []
    for ex in exercises:
        ex_name = ex.get("name", "").strip()
        if not ex_name:
            continue
        cur.execute("""
            INSERT INTO exercises (workout_id, name, sets, reps, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (workout_id, ex_name, ex.get("sets", 0), ex.get("reps", 0), ex.get("weight", 0.0)))
        saved_exercises.append(ex_name)

    conn.commit()
    conn.close()

    return jsonify({
        "workout_id": workout_id,
        "client_name": client_name,
        "date": workout_date,
        "workout_type": workout_type,
        "duration_min": duration_min,
        "exercises_saved": saved_exercises,
    }), 201


@app.route("/workout/<client_name>")
def get_workouts(client_name):
    """Return all workout sessions for a client (mirrors v2.2.4 open_workout_history_window)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT w.id, w.date, w.workout_type, w.duration_min, w.notes
        FROM workouts w
        WHERE w.client_name=?
        ORDER BY w.date DESC, w.id DESC
    """, (client_name,)).fetchall()

    result = []
    for row in rows:
        workout = dict(row)
        ex_rows = conn.execute(
            "SELECT name, sets, reps, weight FROM exercises WHERE workout_id=?",
            (row["id"],)
        ).fetchall()
        workout["exercises"] = [dict(e) for e in ex_rows]
        result.append(workout)

    conn.close()
    return jsonify(result)


@app.route("/metrics", methods=["POST"])
def log_metrics():
    """Log body metrics for a client (mirrors v2.2.4 open_log_metrics_window)."""
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    metric_date = data.get("date", date.today().isoformat())
    weight = data.get("weight")
    waist = data.get("waist")
    bodyfat = data.get("bodyfat")

    if not client_name:
        return jsonify({"error": "client_name is required"}), 400
    if not metric_date:
        return jsonify({"error": "date is required"}), 400

    conn = get_db()
    conn.execute("""
        INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
        VALUES (?, ?, ?, ?, ?)
    """, (client_name, metric_date, weight, waist, bodyfat))
    conn.commit()
    conn.close()

    return jsonify({
        "client_name": client_name,
        "date": metric_date,
        "weight_kg": weight,
        "waist_cm": waist,
        "bodyfat_pct": bodyfat,
    }), 201


@app.route("/metrics/<client_name>")
def get_metrics(client_name):
    """Return all body metric entries for a client."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM metrics WHERE client_name=? ORDER BY date DESC",
        (client_name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/metrics/chart/<client_name>")
def weight_trend_chart(client_name):
    """Return a weight trend chart PNG (mirrors v2.2.4 show_weight_chart)."""
    conn = get_db()
    rows = conn.execute("""
        SELECT date, weight FROM metrics
        WHERE client_name=? AND weight IS NOT NULL
        ORDER BY date
    """, (client_name,)).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": f"No weight metrics for client '{client_name}'"}), 404

    dates = [r["date"] for r in rows]
    weights = [r["weight"] for r in rows]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, weights, marker="o", linewidth=2, color="orange")
    plt.title(f"Weight Trend – {client_name}")
    plt.xlabel("Date")
    plt.ylabel("Weight (kg)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    return Response(buf.getvalue(), mimetype="image/png")


@app.route("/bmi/<client_name>")
def bmi_info(client_name):
    """Return BMI and risk info for a client (mirrors v2.2.4 show_bmi_info)."""
    conn = get_db()
    row = conn.execute(
        "SELECT weight, height FROM clients WHERE name=?", (client_name,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{client_name}' not found"}), 404

    result = calculate_bmi(row["weight"], row["height"])
    if result is None:
        return jsonify({"error": "Valid height and weight required to calculate BMI"}), 400

    return jsonify({"client": client_name, **result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)