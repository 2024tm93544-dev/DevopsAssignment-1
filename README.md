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

ACEest Fitness (Version 3.0.1) is a functional fitness gym management system. Building on previous versions, this release introduces comprehensive workout logging, body metrics tracking, and a BMI calculator.

**Available Programs:**

- **Fat Loss (FL) – 3 day:** 3-day full-body fat loss with a calorie factor of 22 kcal/kg.
- **Fat Loss (FL) – 5 day:** 5-day split, higher volume fat loss with a calorie factor of 24 kcal/kg.
- **Muscle Gain (MG) – PPL:** Push/Pull/Legs hypertrophy with a calorie factor of 35 kcal/kg.
- **Beginner (BG):** 3-day simple beginner full-body with a calorie factor of 26 kcal/kg.

**New in v3.0.1:**

- Support for comprehensive workout and exercise logging (`/workouts`).
- Advanced body metrics tracking including bodyfat and waist measurements (`/metrics`).
- BMI & risk calculator endpoint (`/bmi`).
- Schema expansion to support client height, target weight, and target adherence.
- Dynamic web interface displaying client goals and program details.

---

## Repository Structure

```text
.
├── app.py                  # Core Flask web application
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

Containerize the application using Docker to ensure a consistent environment across different machines.

1. **Build the Docker Image:**

   ```bash
   docker build -t aceest-fitness-app:3.0.1 .
   ```

2. **Run the Container (with Persistence):**
   To ensure your client data persists after stopping the container, mount a local directory to `/app/data`:

   ```bash
   docker run -d -p 5000:5000 --name aceest -v <your-host-path>:/app/data aceest-fitness-app:3.0.1
   ```

3. **Stop the Container:**
   ```bash
   docker stop aceest
   docker rm aceest
   ```

---

## Testing

The repository uses `pytest` for unit and integration testing. The test suite covers calorie calculations, program lookups, input validation, SQLite persistence, BMI, workout tracking, progress monitoring, and API endpoint behavior.

**Run tests locally:**

```bash
pytest tests/ -v
```

**Run tests inside the Docker container:**

```bash
docker run --rm aceest-fitness-app:3.0.1 pytest tests/ -v
```

---

## CI/CD Pipeline

The project implements an automated Continuous Integration and Continuous Deployment (CI/CD) pipeline to ensure code quality and build stability.

### GitHub Actions

The pipeline triggers automatically on every `push` and `pull_request` to the `main` branch.

**Pipeline Stages (`.github/workflows/main.yml`):**

1. **Build & Lint:** Installs dependencies and checks for syntax errors using `flake8`.
2. **Docker Build:** Validates the container build process by building the Docker image.
3. **Test:** Executes the `pytest` suite inside the newly built Docker container to ensure behavior consistency.

### Jenkins

Jenkins serves as an independent build server, acting as a secondary validation gate outside of the continuous integration environment.

**Configuration Overview:**

1. Configure a Freestyle project connected to your GitHub repository.
2. Trigger builds using SCM polling or GitHub webhooks.
3. Execute shell steps to build and validate:
   ```bash
   pip install -r requirements.txt
   docker build -t aceest-fitness-app:3.0.1 .
   ```

---

## API Reference

The service provides a simple REST API to interact with the gym's database.

| Method | Endpoint                 | Description                                                    | Example Payload/Query                                                               |
| ------ | ------------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `GET`  | `/`                      | Web interface listing gym programs and client list             | N/A                                                                                 |
| `GET`  | `/programs`              | Returns all available fitness programs as JSON                 | N/A                                                                                 |
| `POST` | `/client`                | Register or update a client with a program                     | `{"name": "Ravi", "program": "Fat Loss (FL) – 3 day", "height": 175, "weight": 75}` |
| `GET`  | `/client/<name>`         | Load a client profile by name                                  | `/client/Ravi`                                                                      |
| `GET`  | `/clients`               | Returns the full client list as JSON                           | N/A                                                                                 |
| `POST` | `/workouts`              | Log a workout session & exercises                              | `{"client_name": "Ravi", "workout_type": "Strength", "duration_min": 60}`           |
| `GET`  | `/workouts/<name>`       | Retrieve workout history for a client                          | `/workouts/Ravi`                                                                    |
| `POST` | `/metrics`               | Save body metrics (weight, bodyfat, etc)                       | `{"client_name": "Ravi", "weight": 74, "bodyfat": 14.5}`                            |
| `GET`  | `/metrics/<name>`        | Retrieve recorded body metrics history                         | `/metrics/Ravi`                                                                     |
| `GET`  | `/metrics/chart/<name>`  | Download a generated PNG weight trend chart                    | `/metrics/chart/Ravi`                                                               |
| `GET`  | `/bmi`                   | Evaluate BMI metrics and health categories                     | `?height=180&weight=80`                                                             |
| `POST` | `/progress`              | Save weekly adherence for a client                             | `{"client_name": "Ravi", "adherence": 85}`                                          |
| `GET`  | `/progress/<name>`       | Returns all progress entries for a client                      | `/progress/Ravi`                                                                    |
| `GET`  | `/progress/chart/<name>` | Download a generated PNG adherence progress chart              | `/progress/chart/Ravi`                                                              |
| `GET`  | `/calories`              | Calculate estimated daily calories based on weight and program | `?weight=80&program=Muscle Gain (MG) – PPL`                                         |

---

## Legacy Versions

The `versions/` directory contains legacy Tkinter scripts (e.g., `Aceestver-X.X.py`). These files represent earlier desktop iterations of the application. They are preserved for historical context and educational purposes but are no longer actively maintained or integrated into the current web service.

---

_Developed for Introduction to DevOps, BITS Pilani (S2-25)_
