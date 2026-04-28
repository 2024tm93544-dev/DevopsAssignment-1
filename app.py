from flask import Flask, jsonify, request, render_template_string, Response
import sqlite3
import os
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import random
from fpdf import FPDF

app = Flask(__name__)

DB_NAME = os.environ.get("ACEEST_DB", "aceest_fitness.db")
AB_VARIANT = os.environ.get("AB_VARIANT", "A")

# Core data store — translated from ACEest v3.0.1 Tkinter desktop application
PROGRAMS = {
    "Fat Loss (FL) – 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) – 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) – PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the clients and progress tables if they don't exist."""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password, role) "
        "VALUES ('admin','admin','Admin')"
    )
    
    cur.execute("PRAGMA table_info(clients)")
    cols = [row[1] for row in cur.fetchall()]
    required = {"id", "name", "age", "height", "weight", "program", "calories", "target_weight", "target_adherence", "membership_status", "membership_end"}
    if not required.issubset(set(cols)):
        cur.execute("DROP TABLE IF EXISTS clients")

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
            target_adherence INTEGER,
            membership_status TEXT,
            membership_end TEXT
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
    """Return estimated daily calorie target."""
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
        header { background: {{ '#1a73e8' if variant == 'B' else '#d4af37' }}; padding: 20px; text-align: center; }
        header h1 { color: {{ '#fff' if variant == 'B' else '#000' }}; margin: 0; }
        .variant-banner { background: {{ '#1a73e8' if variant == 'B' else '#2e7d32' }}; color: #fff; text-align: center; padding: 6px; font-size: 13px; font-weight: bold; letter-spacing: 1px; }
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
    <div class="variant-banner">{{ 'B-SITE — Variant B (New Version Under Test)' if variant == 'B' else 'A-SITE — Variant A (Stable)' }}</div>
    <header><h1>ACEest Functional Fitness System v3.2.4{{ ' [B]' if variant == 'B' else '' }}</h1></header>
    <main>
        <h2>Available Programs</h2>
        <div class="programs">
            {% for key, p in programs.items() %}
            <div class="card">
                <h2>{{ key }}</h2>
                <p>Calorie Factor: {{ p.factor }} kcal/kg</p>
                {% if p.desc %}<p><i>{{ p.desc }}</i></p>{% endif %}
            </div>
            {% endfor %}
        </div>
        {% if clients %}
        <h2>Client List</h2>
        <table>
            <tr><th>Name</th><th>Age</th><th>Height</th><th>Weight</th><th>Program</th><th>Calories</th><th>Target Wt</th><th>Target Adh</th><th>Membership Status</th><th>Membership End</th></tr>
            {% for c in clients %}
            <tr>
                <td>{{ c.name }}</td>
                <td>{{ c.age or '-' }}</td>
                <td>{{ c.height or '-' }} cm</td>
                <td>{{ c.weight or '-' }} kg</td>
                <td>{{ c.program }}</td>
                <td>{{ c.calories or '-' }} kcal/day</td>
                <td>{{ c.target_weight or '-' }} kg</td>
                <td>{{ c.target_adherence or '-' }}%</td>
                <td>{{ c.membership_status or '-' }}</td>
                <td>{{ c.membership_end or '-' }}</td>
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
    rows = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    client_list = [dict(r) for r in rows]
    return render_template_string(INDEX_HTML, programs=PROGRAMS, clients=client_list, variant=AB_VARIANT)


@app.route("/programs")
def get_programs():
    return jsonify(PROGRAMS)


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    conn = get_db()
    row = conn.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    conn.close()

    if row:
        return jsonify({"message": "Login successful", "role": row["role"], "user_id": row["id"]}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route("/client", methods=["POST"])
def register_client():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    target_weight = data.get("target_weight")
    target_adherence = data.get("target_adherence")
    program_key = data.get("program", "").strip()
    membership_status = data.get("membership_status", "Active").strip()
    membership_end = data.get("membership_end", "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not program_key:
        return jsonify({"error": "program is required"}), 400
    if program_key not in PROGRAMS:
        return jsonify({"error": f"unknown program '{program_key}'"}), 400

    calories = calculate_calories(weight if weight else 0, program_key)

    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO clients (name, age, height, weight, program, calories, target_weight, target_adherence, membership_status, membership_end)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, height, weight, program_key, calories, target_weight, target_adherence, membership_status, membership_end))
    conn.commit()
    conn.close()

    return jsonify({
        "client": name,
        "age": age,
        "height_cm": height,
        "weight_kg": weight,
        "program": program_key,
        "calories": calories,
        "target_weight": target_weight,
        "target_adherence": target_adherence,
        "membership_status": membership_status,
        "membership_end": membership_end,
    }), 201


@app.route("/client/<name>")
def load_client(name):
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{name}' not found"}), 404

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "age": row["age"],
        "height": row["height"],
        "weight": row["weight"],
        "program": row["program"],
        "calories": row["calories"],
        "target_weight": row["target_weight"],
        "target_adherence": row["target_adherence"],
        "membership_status": row["membership_status"],
        "membership_end": row["membership_end"],
    })


@app.route("/membership/<client_name>")
def check_membership(client_name):
    conn = get_db()
    row = conn.execute("SELECT membership_status, membership_end FROM clients WHERE name=?", (client_name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{client_name}' not found"}), 404

    return jsonify({
        "client_name": client_name,
        "membership_status": row["membership_status"],
        "membership_end": row["membership_end"],
    })


@app.route("/clients")
def list_clients():
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/progress", methods=["POST"])
def save_progress():
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
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM progress WHERE client_name=?", (client_name,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/progress/chart/<client_name>")
def progress_chart(client_name):
    conn = get_db()
    rows = conn.execute(
        "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id", 
        (client_name,)
    ).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": f"No progress data available for client '{client_name}'"}), 404

    weeks = [r["week"] for r in rows]
    adherence = [r["adherence"] for r in rows]

    plt.figure(figsize=(8, 4))
    plt.plot(weeks, adherence, marker="o", linewidth=2)
    plt.title(f"Weekly Adherence Progress – {client_name}")
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


@app.route("/workouts", methods=["POST"])
def log_workout():
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    w_date = data.get("date", datetime.now().strftime("%Y-%m-%d")).strip()
    w_type = data.get("workout_type", "").strip()
    duration = data.get("duration_min", 60)
    notes = data.get("notes", "")

    if not client_name or not w_date or not w_type:
        return jsonify({"error": "client_name, date, and workout_type are required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (client_name, w_date, w_type, duration, notes))
    workout_id = cur.lastrowid
    
    ex_name = data.get("exercise_name")
    if ex_name:
        ex_sets = data.get("sets", 3)
        ex_reps = data.get("reps", 10)
        ex_weight = data.get("exercise_weight", 0.0)
        cur.execute("""
            INSERT INTO exercises (workout_id, name, sets, reps, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (workout_id, ex_name, ex_sets, ex_reps, ex_weight))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Workout logged", "workout_id": workout_id}), 201


@app.route("/workouts/<client_name>")
def get_workouts(client_name):
    conn = get_db()
    rows = conn.execute("""
        SELECT date, workout_type, duration_min, notes 
        FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC
    """, (client_name,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/metrics", methods=["POST"])
def log_metrics():
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    m_date = data.get("date", datetime.now().strftime("%Y-%m-%d")).strip()
    weight = data.get("weight")
    waist = data.get("waist")
    bodyfat = data.get("bodyfat")

    if not client_name or not m_date:
        return jsonify({"error": "client_name and date are required"}), 400

    conn = get_db()
    conn.execute("""
        INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
        VALUES (?, ?, ?, ?, ?)
    """, (client_name, m_date, weight, waist, bodyfat))
    
    if weight is not None and float(weight) > 0:
        conn.execute("UPDATE clients SET weight=? WHERE name=?", (weight, client_name))
        
    conn.commit()
    conn.close()
    return jsonify({"message": "Metrics logged"}), 201


@app.route("/metrics/<client_name>")
def get_metrics(client_name):
    conn = get_db()
    rows = conn.execute("SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name=? ORDER BY date DESC", (client_name,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/metrics/chart/<client_name>")
def metrics_chart(client_name):
    conn = get_db()
    rows = conn.execute("SELECT date, weight FROM metrics WHERE client_name=? AND weight IS NOT NULL ORDER BY date", (client_name,)).fetchall()
    conn.close()

    if not rows:
        return jsonify({"error": f"No weight metrics available for client '{client_name}'"}), 404

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


@app.route("/bmi")
def get_bmi():
    try:
        height = float(request.args.get("height", 0))
        weight = float(request.args.get("weight", 0))
    except ValueError:
        return jsonify({"error": "height and weight must be numbers"}), 400

    if height <= 0 or weight <= 0:
        return jsonify({"error": "height and weight must be positive numbers"}), 400

    h_m = height / 100.0
    bmi = weight / (h_m * h_m)
    bmi = round(bmi, 1)

    if bmi < 18.5:
        category = "Underweight"
        risk = "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category = "Normal"
        risk = "Low risk if active and strong."
    elif bmi < 30:
        category = "Overweight"
        risk = "Moderate risk; focus on adherence and progressive activity."
    else:
        category = "Obese"
        risk = "Higher risk; prioritize fat loss, consistency, and supervision."

    return jsonify({
        "height_cm": height,
        "weight_kg": weight,
        "bmi": bmi,
        "category": category,
        "risk": risk
    })


@app.route("/ai_program", methods=["POST"])
def generate_ai_program():
    data = request.get_json(silent=True) or {}
    client_name = data.get("client_name", "").strip()
    exp_level = data.get("experience_level", "").strip().lower()

    if not client_name:
        return jsonify({"error": "client_name is required"}), 400
    if not exp_level or exp_level not in ["beginner", "intermediate", "advanced"]:
        return jsonify({"error": "experience_level must be beginner, intermediate, or advanced"}), 400

    conn = get_db()
    row = conn.execute("SELECT program FROM clients WHERE name=?", (client_name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{client_name}' not found"}), 404
        
    program_name = row["program"]

    exercises_pool = {
        "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
        "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown", "Lateral Raise", "Bicep Curl", "Tricep Extension"],
        "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"],
        "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
    }

    focus = "Full Body"
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"

    if exp_level == "beginner":
        sets_range = (2, 3)
        reps_range = (8, 12)
        days = 3
    elif exp_level == "intermediate":
        sets_range = (3, 4)
        reps_range = (8, 15)
        days = 4
    else:
        sets_range = (4, 5)
        reps_range = (6, 15)
        days = 5

    weekly_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][:days]
    schedule = []

    for day in weekly_days:
        exercises = random.sample(exercises_pool[focus], k=3 if days < 4 else 4)
        day_plan = []
        for ex in exercises:
            day_plan.append({
                "exercise": ex,
                "sets": random.randint(*sets_range),
                "reps": random.randint(*reps_range)
            })
        schedule.append({"day": day, "routines": day_plan})

    return jsonify({
        "client_name": client_name,
        "experience_level": exp_level,
        "focus": focus,
        "schedule": schedule
    }), 200


@app.route("/export_pdf/<client_name>")
def export_pdf(client_name):
    conn = get_db()
    row = conn.execute("SELECT * FROM clients WHERE name=?", (client_name,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": f"client '{client_name}' not found"}), 404

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Client Report - {client_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    
    pdf.ln(10)
    pdf.cell(0, 10, f"Name: {row['name']}", ln=True)
    pdf.cell(0, 10, f"Age: {row['age'] or '-'}", ln=True)
    pdf.cell(0, 10, f"Height: {row['height'] or '-'} cm", ln=True)
    pdf.cell(0, 10, f"Weight: {row['weight'] or '-'} kg", ln=True)
    program_name = str(row['program']).replace('–', '-') if row['program'] else ''
    pdf.cell(0, 10, f"Program: {program_name}", ln=True)
    pdf.cell(0, 10, f"Membership Status: {row['membership_status'] or '-'}", ln=True)
    pdf.cell(0, 10, f"Membership End: {row['membership_end'] or '-'}", ln=True)
    
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename={client_name}_report.pdf"}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
