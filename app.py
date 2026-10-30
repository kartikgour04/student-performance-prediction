"""StudyPulse - Student Performance Prediction website (Flask backend).

Start with:  python app.py      then open  http://localhost:5000

Pages (HTML)  : /  /login  /register  /dashboard (students)  /admin (teachers)
JSON API      : /api/...  (the JavaScript in static/js calls these)
"""
import hmac
import json
import logging
import os
import re
from functools import wraps

import numpy as np
import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, session
from pymongo.errors import PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash

from src import database as dbm
from src.prediction import advice_for, level_for, models_exist, predict_many, predict_student, reload_models
from src.preprocessing import PASS_MARK, validate_inputs, validate_student
from src.training import METRICS_FILE, train_and_evaluate

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev-only-secret-change-me"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 7)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_db = None


def db():
    """One shared database connection, created the first time it is needed."""
    global _db
    if _db is None:
        _db = dbm.get_db()
    return _db


# ---------------------------------------------------------------- helpers
def error(message, status=400):
    return jsonify({"error": message}), status


def to_number(value):
    """Turn user input into a float, or None if it is not a normal number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def login_required(role=None):
    """Protect an API route. role='teacher' limits it to teachers."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return error("Please log in first.", 401)
            if role and session.get("role") != role:
                return error("You do not have permission to do this.", 403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def page_login_required(role):
    """Protect a page. Wrong or missing login -> go to the right place."""
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect("/login")
            if session.get("role") != role:
                return redirect("/admin" if session.get("role") == "teacher" else "/dashboard")
            return view(*args, **kwargs)
        return wrapper
    return decorator


def start_session(user):
    session.clear()
    session.permanent = True
    session.update(user_id=user["id"], name=user["name"], email=user["email"], role=user["role"])


def current_user():
    return {"name": session["name"], "email": session["email"], "role": session["role"]}


@app.errorhandler(dbm.DatabaseError)
@app.errorhandler(PyMongoError)
def database_problem(exc):
    """Users see a calm message; the technical detail goes to the terminal."""
    logging.error("Database problem: %s", exc)
    return error("We can't reach our servers right now. Please try again in a moment.", 503)


# ---------------------------------------------------------------- pages
@app.get("/")
def home_page():
    return render_template("index.html")


@app.get("/login")
def login_page():
    if "user_id" in session:
        return redirect("/admin" if session["role"] == "teacher" else "/dashboard")
    return render_template("login.html")


@app.get("/register")
def register_page():
    if "user_id" in session:
        return redirect("/admin" if session["role"] == "teacher" else "/dashboard")
    return render_template("register.html")


@app.get("/dashboard")
@page_login_required("student")
def dashboard_page():
    return render_template("dashboard.html", user=current_user())


@app.get("/admin")
@page_login_required("teacher")
def admin_page():
    return render_template("admin.html", user=current_user())


# ---------------------------------------------------------------- accounts
@app.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = "teacher" if data.get("role") == "teacher" else "student"

    if len(name) < 2:
        return error("Please enter your name.")
    if not EMAIL_PATTERN.match(email):
        return error("Please enter a valid email address.")
    if len(password) < 6:
        return error("Your password must be at least 6 characters.")

    class_code = teacher_id = None
    if role == "teacher":
        # Teachers need the secret access code from .env, so students cannot make teacher accounts.
        expected = os.getenv("TEACHER_CODE", "")
        given = str(data.get("teacher_code", "")).strip()
        if not expected:
            return error("Teacher sign-up is not available on this site.", 403)
        if not hmac.compare_digest(given.encode(), expected.encode()):
            return error("The teacher access code is not correct.", 403)
        class_code = dbm.new_class_code(db())
    else:
        code = str(data.get("class_code", "")).strip().upper()
        if code:  # optional: join a teacher's class while signing up
            teacher = dbm.find_teacher_by_code(db(), code)
            if not teacher:
                return error("We couldn't find that class code. Check it with your teacher, or leave it empty and join later.")
            teacher_id = teacher["id"]

    ok, result = dbm.create_user(db(), name, email, generate_password_hash(password),
                                 role, class_code, teacher_id)
    if not ok:
        return error(result, 409)
    start_session(result)
    return jsonify({"redirect": "/admin" if role == "teacher" else "/dashboard"})


@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = dbm.find_user_by_email(db(), email)
    if not user or not check_password_hash(user["password_hash"], password):
        return error("Wrong email or password.", 401)  # same message for both, on purpose
    start_session(user)
    return jsonify({"redirect": "/admin" if user["role"] == "teacher" else "/dashboard"})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"redirect": "/"})


# ---------------------------------------------------------------- student features
@app.post("/api/predict")
@login_required()
def api_predict():
    data = request.get_json(silent=True) or {}
    hours = to_number(data.get("study_hours"))
    attendance = to_number(data.get("attendance"))
    previous = to_number(data.get("previous_marks"))

    problems = validate_inputs(hours, attendance, previous)
    if problems:
        return error(" ".join(problems))
    if not models_exist():
        return error("Predictions are not available yet. Please ask your teacher to set them up.", 503)

    prediction = predict_student(hours, attendance, previous)
    advice = advice_for(hours, attendance, previous, prediction)
    dbm.save_prediction(
        db(), session["user_id"],
        {"study_hours": hours, "attendance": attendance, "previous_marks": previous},
        prediction["predicted_marks"], prediction["result"], prediction["pass_probability"],
    )
    return jsonify({**prediction, **advice, "pass_mark": PASS_MARK})


@app.get("/api/predictions")
@login_required()
def api_predictions():
    return jsonify(dbm.get_user_predictions(db(), session["user_id"]))


@app.get("/api/my-class")
@login_required("student")
def api_my_class():
    """Which teacher (if any) this student has joined."""
    me = dbm.find_user_by_id(db(), session["user_id"])
    teacher = dbm.find_user_by_id(db(), me.get("teacher_id")) if me and me.get("teacher_id") else None
    return jsonify({"joined": bool(teacher), "teacher_name": teacher["name"] if teacher else None})


@app.post("/api/join-class")
@login_required("student")
def api_join_class():
    code = str((request.get_json(silent=True) or {}).get("class_code", "")).strip().upper()
    if not code:
        return error("Please enter the class code your teacher gave you.")
    teacher = dbm.find_teacher_by_code(db(), code)
    if not teacher:
        return error("We couldn't find that class code. Please check it with your teacher.", 404)
    dbm.set_teacher(db(), session["user_id"], teacher["id"])
    return jsonify({"joined": True, "teacher_name": teacher["name"]})


# ---------------------------------------------------------------- teacher: my class
@app.get("/api/admin/class")
@login_required("teacher")
def api_class():
    """The students who joined THIS teacher's class, with their latest forecast."""
    teacher = dbm.find_user_by_id(db(), session["user_id"])
    if not teacher:
        return error("Please log in again.", 401)
    if not teacher.get("class_code"):  # older accounts get a code the first time
        teacher["class_code"] = dbm.new_class_code(db())
        dbm.set_class_code(db(), teacher["id"], teacher["class_code"])

    students = dbm.get_class_students(db(), teacher["id"])
    summaries = dbm.get_prediction_summaries(db(), [s["id"] for s in students])

    rows = []
    for s in students:
        info = summaries.get(s["id"])
        latest = None
        if info:
            last = info["latest"]
            latest = {
                "predicted_marks": last["predicted_marks"],
                "pass_chance": round(last["pass_probability"] * 100),
                "level": level_for(last["pass_probability"]),
                "study_hours": last["study_hours"],
                "attendance": last["attendance"],
                "previous_marks": last["previous_marks"],
                "created_at": last["created_at"].isoformat(),
            }
        rows.append({"id": s["id"], "name": s["name"], "email": s["email"],
                     "checks": info["count"] if info else 0, "latest": latest})

    rank = {"risk": 0, "ok": 1, "great": 2}  # students who need help first, never-checked last
    rows.sort(key=lambda r: (rank.get(r["latest"]["level"], 3) if r["latest"] else 3, r["name"].lower()))
    checked = [r for r in rows if r["latest"]]
    return jsonify({
        "teacher_name": teacher["name"],
        "class_code": teacher["class_code"],
        "total": len(rows),
        "checked": len(checked),
        "need_support": sum(1 for r in checked if r["latest"]["level"] == "risk"),
        "average_forecast": round(sum(r["latest"]["predicted_marks"] for r in checked) / len(checked), 1) if checked else None,
        "students": rows,
    })


@app.get("/api/admin/class/<student_user_id>/history")
@login_required("teacher")
def api_class_history(student_user_id):
    student = dbm.find_user_by_id(db(), student_user_id)
    # A teacher can only open students who joined their own class.
    if not student or student["role"] != "student" or student.get("teacher_id") != session["user_id"]:
        return error("That student is not in your class.", 404)
    return jsonify({"name": student["name"], "history": dbm.get_user_predictions(db(), student_user_id, 50)})


# ---------------------------------------------------------------- teacher: overview
@app.get("/api/admin/summary")
@login_required("teacher")
def api_summary():
    students = dbm.get_students(db(), session["user_id"])  # only this teacher's records
    if not students:
        return jsonify({"total": 0})
    df = pd.DataFrame(students)
    passed = df["exam_marks"] >= PASS_MARK

    # marks groups: 0-19, 20-39, 40-59, 60-79, 80-100
    groups = np.minimum((df["exam_marks"] // 20).astype(int), 4)
    distribution = np.bincount(groups, minlength=5).tolist()

    needs_support = []
    if models_exist():
        df = df.join(predict_many(df))
        risky = df[df["pass_probability"] < 0.6].sort_values("pass_probability").head(8)
        needs_support = [
            {"student_id": r.student_id, "study_hours": r.study_hours, "attendance": r.attendance,
             "previous_marks": r.previous_marks, "pass_chance": round(float(r.pass_probability) * 100)}
            for r in risky.itertuples()
        ]

    return jsonify({
        "total": len(df),
        "average_marks": round(float(df["exam_marks"].mean()), 1),
        "pass_rate": round(float(passed.mean()) * 100, 1),
        "average_study_hours": round(float(df["study_hours"].mean()), 1),
        "average_attendance": round(float(df["attendance"].mean()), 1),
        "passed": int(passed.sum()),
        "failed": int((~passed).sum()),
        "distribution": distribution,
        "scatter_pass": df[passed][["study_hours", "exam_marks"]].rename(columns={"study_hours": "x", "exam_marks": "y"}).to_dict("records"),
        "scatter_fail": df[~passed][["study_hours", "exam_marks"]].rename(columns={"study_hours": "x", "exam_marks": "y"}).to_dict("records"),
        "needs_support": needs_support,
    })


# ---------------------------------------------------------------- teacher: student records (CRUD)
def read_student_form(data, student_id=None):
    """Validate the form sent by the teacher. Returns (record, error_text)."""
    student_id = (student_id or str(data.get("student_id", ""))).strip().upper()
    values = {k: to_number(data.get(k)) for k in ("study_hours", "attendance", "previous_marks", "exam_marks")}
    problems = validate_student(student_id, **values)
    if problems:
        return None, " ".join(problems)
    return {"student_id": student_id, **values}, None


@app.get("/api/admin/students")
@login_required("teacher")
def api_students():
    return jsonify(dbm.get_students(db(), session["user_id"]))


@app.post("/api/admin/students")
@login_required("teacher")
def api_add_student():
    record, problem = read_student_form(request.get_json(silent=True) or {})
    if problem:
        return error(problem)
    ok, message = dbm.insert_student(db(), record, session["user_id"])
    return (jsonify({"message": message}), 201) if ok else error(message, 409)


@app.put("/api/admin/students/<student_id>")
@login_required("teacher")
def api_update_student(student_id):
    record, problem = read_student_form(request.get_json(silent=True) or {}, student_id)
    if problem:
        return error(problem)
    record.pop("student_id")
    ok, message = dbm.update_student(db(), session["user_id"], student_id.upper(), record)
    return jsonify({"message": message}) if ok else error(message, 404)


@app.delete("/api/admin/students/<student_id>")
@login_required("teacher")
def api_delete_student(student_id):
    ok, message = dbm.delete_student(db(), session["user_id"], student_id.upper())
    return jsonify({"message": message}) if ok else error(message, 404)


# ---------------------------------------------------------------- teacher: prediction quality
@app.get("/api/admin/model")
@login_required("teacher")
def api_model():
    evaluation = dbm.get_latest_evaluation(db())
    if evaluation:
        evaluation["created_at"] = evaluation["created_at"].isoformat()
    elif METRICS_FILE.exists():
        evaluation = json.loads(METRICS_FILE.read_text())
    else:
        return jsonify({"trained": False})
    return jsonify({"trained": True, **evaluation})


@app.post("/api/admin/retrain")
@login_required("teacher")
def api_retrain():
    # The forecast model is shared. It learns from every teacher's records, but only the
    # numbers are used: no teacher can see another teacher's records.
    records = dbm.get_training_records(db())
    if len(records) < 30:
        return error("At least 30 exam records are needed to update the forecasts.")
    try:
        evaluation = train_and_evaluate(pd.DataFrame(records), "Exam records from all teachers")
    except ValueError as problem:
        return error(str(problem))
    dbm.save_evaluation(db(), evaluation)
    reload_models()
    return jsonify({"message": "Predictions were updated using the latest student records."})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=False)
