from flask import Flask, jsonify, request, render_template_string, Response
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_NAME = os.environ.get("ACEEST_DB", "aceest_fitness.db")

# Core data store — translated from ACEest v2.1.2 Tkinter desktop application
PROGRAMS = {
    "Fat Loss (FL)": {"factor": 22},
    "Muscle Gain (MG)": {"factor": 35},
    "Beginner (BG)": {"factor": 26},
}


# ---------------------------------------------------------------------------
# Database helpers (mirrors v2.1.2 init_db)
# ---------------------------------------------------------------------------

def get_db():
    """Return a new SQLite connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the clients and progress tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            weight REAL,
            program TEXT,
            calories INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            week TEXT,
            adherence INTEGER
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
    calories = int(weight_kg * factor)
    return calories


# ---------------------------------------------------------------------------
# HTML template
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
        pre { color: #ccc; white-space: pre-wrap; }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #d4af37; }
    </style>
</head>
<body>
    <header><h1>ACEest Functional Fitness System v2.1.2</h1></header>
    <main>
        <h2>Available Programs</h2>
        <div class="programs">
            {% for key, p in programs.items() %}
            <div class="card">
                <h2>{{ key }}</h2>
                <p>Calorie Factor: {{ p.factor }} kcal/kg</p>
            </div>
            {% endfor %}
        </div>
        {% if clients %}
        <h2>Client List</h2>
        <table>
            <tr><th>Name</th><th>Age</th><th>Weight</th><th>Program</th><th>Calories</th></tr>
            {% for c in clients %}
            <tr>
                <td>{{ c.name }}</td><td>{{ c.age }}</td><td>{{ c.weight }}</td>
                <td>{{ c.program }}</td><td>{{ c.calories }} kcal/day</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
    </main>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("SELECT name, age, weight, program, calories FROM clients").fetchall()
    conn.close()
    client_list = [dict(r) for r in rows]
    return render_template_string(INDEX_HTML, programs=PROGRAMS, clients=client_list)


@app.route("/programs")
def get_programs():
    return jsonify(PROGRAMS)


@app.route("/client", methods=["POST"])
def register_client():
    """Register or update a client (mirrors v2.1.2 save_client)."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    age = data.get("age")
    weight = data.get("weight")
    program_key = data.get("program", "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not program_key:
        return jsonify({"error": "program is required"}), 400
    if program_key not in PROGRAMS:
        return jsonify({"error": f"unknown program '{program_key}'"}), 400

    calories = calculate_calories(weight if weight else 0, program_key)

    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO clients (name, age, weight, program, calories)
        VALUES (?, ?, ?, ?, ?)
    """, (name, age, weight, program_key, calories))
    conn.commit()
    conn.close()

    return jsonify({
        "client": name,
        "age": age,
        "weight_kg": weight,
        "program": program_key,
        "calories": calories,
    }), 201


@app.route("/client/<name>")
def load_client(name):
    """Load a single client by name (mirrors v2.1.2 load_client)."""
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{name}' not found"}), 404

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "age": row["age"],
        "weight": row["weight"],
        "program": row["program"],
        "calories": row["calories"],
    })


@app.route("/clients")
def list_clients():
    """Return the full client list as JSON (from SQLite)."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/progress", methods=["POST"])
def save_progress():
    """Save weekly adherence for a client (mirrors v2.1.2 save_progress)."""
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

    return jsonify({
        "client_name": client_name,
        "week": week,
        "adherence": adherence,
    }), 201


@app.route("/progress/<client_name>")
def get_progress(client_name):
    """Return all progress entries for a given client."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE client_name=?", (client_name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
