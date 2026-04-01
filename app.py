from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# Core data store — translated from ACEest v1.0 Tkinter desktop application
PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": (
            "Mon: 5x5 Back Squat + AMRAP\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: 10RFT Deadlifts/Box Jumps\n"
            "Fri: 30min Active Recovery"
        ),
        "diet": (
            "B: 3 Egg Whites + Oats Idli\n"
            "L: Grilled Chicken + Brown Rice\n"
            "D: Fish Curry + Millet Roti\n"
            "Target: 2,000 kcal"
        ),
        "calorie_target": 2000,
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "B: 4 Eggs + PB Oats\n"
            "L: Chicken Biryani (250g Chicken)\n"
            "D: Mutton Curry + Jeera Rice\n"
            "Target: 3,200 kcal"
        ),
        "calorie_target": 3200,
    },
    "BG": {
        "name": "Beginner",
        "workout": (
            "Circuit Training: Air Squats, Ring Rows, Push-ups.\n"
            "Focus: Technique Mastery & Form (90% Threshold)"
        ),
        "diet": (
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\n"
            "Protein: 120g/day"
        ),
        "calorie_target": 2200,
    },
}

GYM_METRICS = {
    "capacity": 150,
    "area_sqft": 10000,
    "break_even_members": 250,
}

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
    </style>
</head>
<body>
    <header><h1>ACEest FUNCTIONAL FITNESS</h1></header>
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
    </main>
</body>
</html>
"""


def calculate_calories(weight_kg, program_key):
    """Return estimated daily calorie target.

    Uses the program's base target, adjusted linearly for body weight
    relative to an 80 kg reference.  Returns None for unknown programs.
    """
    if program_key not in PROGRAMS:
        return None
    base = PROGRAMS[program_key]["calorie_target"]
    adjusted = int(base * (weight_kg / 80))
    return adjusted


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
    return render_template_string(INDEX_HTML, programs=PROGRAMS, metrics=GYM_METRICS)


@app.route("/programs")
def get_programs():
    return jsonify(PROGRAMS)


@app.route("/client", methods=["POST"])
def register_client():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    goal = data.get("goal", "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not goal:
        return jsonify({"error": "goal is required"}), 400

    program_key = recommend_program(goal)
    program = PROGRAMS[program_key]

    return jsonify({
        "client": name,
        "goal": goal,
        "recommended_program": program_key,
        "program_name": program["name"],
        "workout": program["workout"],
        "diet": program["diet"],
    }), 201


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
