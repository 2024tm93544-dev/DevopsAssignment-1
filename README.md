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

ACEest Fitness is a functional fitness gym management system. The service provides functionalities to view available fitness programs, register clients, recommend programs based on goals, and dynamically calculate daily calorie targets based on the client's weight and program.

**Available Programs:**
- **FL (Fat Loss):** Focused on weight reduction with a mix of strength and conditioning.
- **MG (Muscle Gain):** Hypertrophy and strength-focused routines.
- **BG (Beginner):** Circuit training and technique mastery.

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
   docker build -t aceest-gym:latest .
   ```

2. **Run the Container:**
   ```bash
   docker run -d -p 5000:5000 --name aceest aceest-gym:latest
   ```

3. **Stop the Container:**
   ```bash
   docker stop aceest
   docker rm aceest
   ```

---

## Testing

The repository uses `pytest` for unit and integration testing. The test suite covers calorie calculations, program lookups, input validation, and API endpoint behavior.

**Run tests locally:**
```bash
pytest tests/ -v
```

**Run tests inside the Docker container:**
```bash
docker run --rm aceest-gym:latest pytest tests/ -v
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
   docker build -t aceest-gym:latest .
   ```

---

## API Reference

The service provides a simple REST API to interact with the gym's database.

| Method | Endpoint | Description | Example Payload/Query |
|---|---|---|---|
| `GET` | `/` | Web interface listing gym programs and metrics | N/A |
| `GET` | `/programs` | Returns all available fitness programs as JSON | N/A |
| `POST` | `/client` | Register a client and get a program recommendation | `{"name": "John", "goal": "muscle gain"}` |
| `GET` | `/calories` | Calculate estimated daily calories based on weight and program | `?weight=80&program=MG` |

---

## Legacy Versions

The `versions/` directory contains legacy Tkinter scripts (e.g., `Aceestver-X.X.py`). These files represent earlier desktop iterations of the application. They are preserved for historical context and educational purposes but are no longer actively maintained or integrated into the current web service.

---

*Developed for Introduction to DevOps, BITS Pilani (S2-25)*
