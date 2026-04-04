# ACEest Fitness & Gym Management Service

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey.svg)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue.svg)
![CI/CD](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-brightgreen.svg)

A comprehensive Flask-based gym management web service. This repository demonstrates a complete DevOps lifecycle—encompassing version control, containerization, automated testing, and CI/CD pipelines via GitHub Actions and Jenkins.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
  - [GitHub Actions](#github-actions)
  - [Jenkins](#jenkins)
- [API Reference](#api-reference)
- [Legacy Versions](#legacy-versions)

---

## Overview

ACEest Fitness (Version 2.2.4) is a functional fitness gym management system. Building on v2.2.1, this release introduces workout session logging, body metric tracking, weight trend charts, BMI analysis, and expanded program options.

**Available Programs:**

- **Fat Loss (FL) – 3 day:** 3-day full-body fat loss with a calorie factor of 22 kcal/kg.
- **Fat Loss (FL) – 5 day:** 5-day split, higher volume fat loss with a calorie factor of 24 kcal/kg.
- **Muscle Gain (MG) – PPL:** Push/Pull/Legs hypertrophy with a calorie factor of 35 kcal/kg.
- **Beginner (BG):** 3-day simple beginner full-body with a calorie factor of 26 kcal/kg.

**New in v2.2.4:**

- **Workout logging** — `/workout` (POST) logs sessions with type, duration, notes, and individual exercises (name, sets, reps, weight).
- **Workout history** — `/workout/<client_name>` (GET) returns full session history including exercises per session.
- **Body metrics logging** — `/metrics` (POST) records weight, waist, and bodyfat % per date.
- **Metrics history** — `/metrics/<client_name>` (GET) returns all logged body metrics.
- **Weight trend chart** — `/metrics/chart/<client_name>` (GET) generates a weight-over-time PNG chart.
- **BMI & risk info** — `/bmi/<client_name>` (GET) calculates BMI and returns category and risk note.
- **Expanded programs** — Fat Loss now has 3-day and 5-day variants; Muscle Gain rebranded to PPL.
- **Client goals** — `/client` (POST) now accepts `target_weight` and `target_adherence` fields.
- **Height field** — Clients now store height (cm) used for BMI calculation.
- **Schema migration** — `init_db()` auto-detects and migrates old v2.2.1 client tables to the new schema.

**New in v2.2.1 (vs v2.1.2):**

- Support for generating and visualizing weekly adherence progress charts via `/progress/chart/<name>`.
- Integrated `matplotlib` as a core dependency for dynamic chart generation.

**Changes in v2.1.2 (vs v2.0.1):**

- Descriptive program keys — programs referenced as full names instead of short codes.
- Simplified program data model — each program only stores its calorie `factor`.
- Cleaner web interface without gym capacity metrics.

---

## Repository Structure

```text
.
├── app.py                  # Core Flask web application (v2.2.4)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image configuration
├── .github/
│   └── workflows/
│       └── main.yml        # GitHub Actions CI/CD pipeline definition
├── tests/
│   └── test_app.py         # Pytest test suite
├── versions/               # Reference files prior to Flask migration
└── README.md               # Project documentation
```

---

## Getting Started

### Local Setup

**Prerequisites:**

- Python 3.11+
- `pip` package manager

1. **Clone the repository:**

   ```bash
   git clone https://github.com/<your-username>/aceest-devops.git
   cd aceest-devops
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:5000`.

### Docker Setup

1. **Build the Docker Image:**

   ```bash
   docker build -t aceest-fitness-app:2.2.4 .
   ```

2. **Run the Container (with Persistence):**

   ```bash
   docker run -d -p 5000:5000 --name aceest -v <your-host-path>:/app/data aceest-fitness-app:2.2.4
   ```

3. **Stop the Container:**
   ```bash
   docker stop aceest
   docker rm aceest
   ```

---

## Testing

```bash
pytest tests/ -v
```

```bash
docker run --rm aceest-fitness-app:2.2.4 pytest tests/ -v
```

---

## CI/CD Pipeline

### GitHub Actions

Triggers on every `push` and `pull_request` to `main`.

1. **Build & Lint** — Installs dependencies, runs `flake8`.
2. **Docker Build** — Validates container build.
3. **Test** — Runs `pytest` inside the built container.

### Jenkins

1. Configure a Freestyle project connected to your GitHub repository.
2. Trigger builds via SCM polling or GitHub webhooks.
3. Shell steps:
   ```bash
   pip install -r requirements.txt
   docker build -t aceest-fitness-app:2.2.4 .
   ```

---

## API Reference

### Existing Endpoints (updated)

| Method | Endpoint | Description | Example Payload/Query |
|--------|----------|-------------|----------------------|
| `GET`  | `/` | Web dashboard — programs and client list | N/A |
| `GET`  | `/programs` | All programs as JSON | N/A |
| `POST` | `/client` | Register/update client (now includes `height`, `target_weight`, `target_adherence`) | `{"name":"Ravi","program":"Fat Loss (FL) – 3 day","age":30,"weight":75,"height":175,"target_weight":68,"target_adherence":85}` |
| `GET`  | `/client/<name>` | Load client profile | `/client/Ravi` |
| `GET`  | `/clients` | Full client list | N/A |
| `POST` | `/progress` | Save weekly adherence | `{"client_name":"Ravi","adherence":85}` |
| `GET`  | `/progress/<name>` | All progress entries | `/progress/Ravi` |
| `GET`  | `/progress/chart/<name>` | Weekly adherence PNG chart | `/progress/chart/Ravi` |
| `GET`  | `/calories` | Calculate daily calorie estimate | `?weight=80&program=Muscle Gain (MG) – PPL` |

### New Endpoints (v2.2.4)

| Method | Endpoint | Description | Example Payload |
|--------|----------|-------------|-----------------|
| `POST` | `/workout` | Log a workout session with exercises | `{"client_name":"Ravi","date":"2025-04-01","workout_type":"Strength","duration_min":60,"notes":"PR on bench","exercises":[{"name":"Bench Press","sets":4,"reps":8,"weight":80}]}` |
| `GET`  | `/workout/<name>` | Full workout history with exercises | `/workout/Ravi` |
| `POST` | `/metrics` | Log body metrics (weight, waist, bodyfat) | `{"client_name":"Ravi","date":"2025-04-01","weight":74.5,"waist":82,"bodyfat":18.2}` |
| `GET`  | `/metrics/<name>` | All body metric entries | `/metrics/Ravi` |
| `GET`  | `/metrics/chart/<name>` | Weight trend PNG chart | `/metrics/chart/Ravi` |
| `GET`  | `/bmi/<name>` | BMI value, category, and risk note | `/bmi/Ravi` |

---

## Legacy Versions

The `versions/` directory contains legacy Tkinter scripts (`Aceestver-X.X.py`). These desktop iterations are preserved for historical context but are no longer actively maintained.

---

_Developed for Introduction to DevOps, BITS Pilani (S2-25)_