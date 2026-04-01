from flask import Flask, jsonify, request, render_template_string, Response
import csv
import io

app = Flask(__name__)

# Core data store — translated from ACEest v1.1.2 Tkinter desktop application
PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": "Back Squat, Cardio, Bench, Deadlift, Recovery",
        "diet": "Egg Whites, Chicken, Fish Curry",
        "calorie_factor": 22,
        "color": "#e74c3c",
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": "Squat, Bench, Deadlift, Press, Rows",
        "diet": "Eggs, Biryani, Mutton Curry",
        "calorie_factor": 35,
        "color": "#2ecc71",
    },
    "BG": {
        "name": "Beginner",
        "workout": "Air Squats, Ring Rows, Push-ups",
        "diet": "Balanced Tamil Meals",
        "calorie_factor": 26,
        "color": "#3498db",
    },
}

GYM_METRICS = {
    "capacity": 150,
    "area_sqft": 10000,
    "break_even_members": 250,
}

# In-memory client store (mirrors v1.1.2 self.clients list)
clients = []

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
        .metrics { background: #333; border-radius: 8px; padding: 15px; margin-top: 30px; font-family: Courier, monospace; }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #d4af37; }
    </style>
</head>
<body>
    <header><h1>ACEest FUNCTIONAL FITNESS SYSTEM v2</h1></header>
    <main>
        <h2>Available Programs</h2>
        <div class="programs">
            {% for key, p in programs.items() %}
            <div class="card">
                <h2>{{ p.name }} ({{ key }})</h2>
                <h3>Workout</h3><pre>{{ p.workout }}</pre>
                <h3>Diet</h3><pre>{{ p.diet }}</pre>
            </div>
            {% endfor %}
        </div>
        <div class="metrics">
            <strong>Gym Metrics:</strong>
            Capacity: {{ metrics.capacity }} users |
            Area: {{ metrics.area_sqft }} sq ft |
            Break-even: {{ metrics.break_even_members }} members
        </div>
        {% if clients %}
        <h2>Client List</h2>
        <table>
            <tr><th>Name</th><th>Age</th><th>Weight</th><th>Program</th><th>Adherence</th><th>Notes</th></tr>
            {% for c in clients %}
            <tr>
                <td>{{ c.name }}</td><td>{{ c.age }}</td><td>{{ c.weight_kg }}</td>
                <td>{{ c.program }}</td><td>{{ c.adherence }}%</td><td>{{ c.notes }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
    </main>
</body>
</html>
"""


def calculate_calories(weight_kg, program_key):
    """Return estimated daily calorie target.

    Uses the program's calorie factor multiplied by body weight.
    Returns None for unknown programs.
    """
    if program_key not in PROGRAMS:
        return None
    factor = PROGRAMS[program_key]["calorie_factor"]
    calories = int(weight_kg * factor)
    return calories


def recommend_program(goal):
    """Map a free-form goal string to a program key."""
    goal_lower = goal.lower()
    if "fat" in goal_lower or "loss" in goal_lower or "cut" in goal_lower:
        return "FL"
    if "muscle" in goal_lower or "gain" in goal_lower or "bulk" in goal_lower:
        return "MG"
    return "BG"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, programs=PROGRAMS,
                                  metrics=GYM_METRICS, clients=clients)


@app.route("/programs")
def get_programs():
    return jsonify(PROGRAMS)


@app.route("/client", methods=["POST"])
def register_client():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    goal = data.get("goal", "").strip()
    age = data.get("age")
    weight = data.get("weight")
    adherence = data.get("adherence", 0)
    notes = data.get("notes", "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not goal:
        return jsonify({"error": "goal is required"}), 400

    program_key = recommend_program(goal)
    program = PROGRAMS[program_key]

    # Store client (mirrors v1.1.2 save_client behaviour)
    client_record = {
        "name": name,
        "age": age,
        "weight_kg": weight,
        "program": program_key,
        "program_name": program["name"],
        "adherence": adherence,
        "notes": notes,
        "goal": goal,
        "workout": program["workout"],
        "diet": program["diet"],
    }
    clients.append(client_record)

    return jsonify({
        "client": name,
        "goal": goal,
        "recommended_program": program_key,
        "program_name": program["name"],
        "workout": program["workout"],
        "diet": program["diet"],
        "adherence": adherence,
        "notes": notes,
    }), 201


@app.route("/clients")
def list_clients():
    """Return the full client list as JSON."""
    return jsonify(clients)


@app.route("/clients/export")
def export_clients_csv():
    """Export the client list as a downloadable CSV file."""
    if not clients:
        return jsonify({"error": "no clients to export"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Age", "Weight", "Program", "Adherence", "Notes"])
    for c in clients:
        writer.writerow([
            c["name"], c["age"], c["weight_kg"],
            c["program"], c["adherence"], c["notes"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=clients.csv"},
    )


@app.route("/clients/chart-data")
def chart_data():
    """Return adherence data for charting (mirrors v1.1.2 progress chart)."""
    return jsonify({
        "names": [c["name"] for c in clients],
        "adherence": [c["adherence"] for c in clients],
    })


@app.route("/calories")
def calories():
    try:
        weight = float(request.args.get("weight", 0))
    except ValueError:
        return jsonify({"error": "weight must be a number"}), 400

    program_key = request.args.get("program", "").upper()

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
