"""All MongoDB work is done here using PyMongo.

Database  : student_performance_db
Collections:
  users             - website accounts (students and teachers); email is UNIQUE
  students          - the student records teachers manage; student_id is UNIQUE
  predictions       - every prediction a user made on the website
  model_evaluations - metrics and model information of each training run
"""
import os
import secrets
from datetime import datetime, timezone

from dotenv import load_dotenv
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConfigurationError, DuplicateKeyError, PyMongoError

load_dotenv()  # reads the .env file

DB_NAME = "student_performance_db"
USERS = "users"
STUDENTS = "students"
EVALUATIONS = "model_evaluations"
PREDICTIONS = "predictions"


class DatabaseError(Exception):
    """A friendly error instead of a long traceback."""


def get_db():
    """Connect to MongoDB and return the database object."""
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise DatabaseError(
            "MONGODB_URI is missing. Copy .env.example to .env and put your MongoDB address in it."
        )
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        client.admin.command("ping")  # makes sure the server is really reachable
    except ConfigurationError as error:
        raise DatabaseError(f"The MONGODB_URI in .env looks wrong: {error}")
    except PyMongoError as error:
        raise DatabaseError(
            "Could not connect to MongoDB. Is MongoDB running (local) or is your Atlas "
            f"URI / IP access list correct? Details: {error}"
        )
    db = client[DB_NAME]
    create_indexes(db)
    return db


def create_indexes(db):
    """Unique indexes: no two students share an ID, no two users share an email."""
    # Exam records belong to a teacher. The same student_id may be used by different teachers,
    # so uniqueness is per teacher. (Older versions had a global unique index: remove it.)
    if "student_id_1" in db[STUDENTS].index_information():
        db[STUDENTS].drop_index("student_id_1")
    db[STUDENTS].create_index([("teacher_id", 1), ("student_id", 1)], unique=True)
    db[USERS].create_index("email", unique=True)
    db[USERS].create_index("class_code", unique=True, sparse=True)  # only teachers have one
    db[USERS].create_index("teacher_id")
    db[PREDICTIONS].create_index([("user_id", 1), ("created_at", -1)])


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- users
CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, so codes are easy to read out


def new_class_code(db):
    """A short unique code (like K7M4QX) that a teacher shares with students."""
    while True:
        code = "".join(secrets.choice(CODE_LETTERS) for _ in range(6))
        if not db[USERS].find_one({"class_code": code}):
            return code


def create_user(db, name, email, password_hash, role="student", class_code=None, teacher_id=None):
    """Create an account. Returns (True, user_dict) or (False, message).

    Teachers get a class_code. Students may have a teacher_id (the teacher they joined).
    """
    user = {"name": name, "email": email, "password_hash": password_hash,
            "role": role, "created_at": _now()}
    if class_code:
        user["class_code"] = class_code
    if teacher_id:
        user["teacher_id"] = teacher_id
    try:
        result = db[USERS].insert_one(user)
    except DuplicateKeyError:
        return False, "An account with this email already exists."
    except PyMongoError as error:
        return False, f"Database error: {error}"
    user["id"] = str(result.inserted_id)
    return True, user


def find_user_by_email(db, email):
    """Returns the user document (with 'id' added) or None."""
    user = db[USERS].find_one({"email": email})
    if user:
        user["id"] = str(user.pop("_id"))
    return user


def _with_id(user):
    """Turn MongoDB's _id into a plain text 'id' and never return the password hash."""
    if user:
        user["id"] = str(user.pop("_id"))
        user.pop("password_hash", None)
    return user


def find_user_by_id(db, user_id):
    try:
        return _with_id(db[USERS].find_one({"_id": ObjectId(user_id)}))
    except (InvalidId, TypeError):
        return None


def find_teacher_by_code(db, class_code):
    return _with_id(db[USERS].find_one({"role": "teacher", "class_code": class_code}))


def set_class_code(db, user_id, class_code):
    db[USERS].update_one({"_id": ObjectId(user_id)}, {"$set": {"class_code": class_code}})


def set_teacher(db, student_user_id, teacher_id):
    """A student joins a teacher's class."""
    db[USERS].update_one({"_id": ObjectId(student_user_id)}, {"$set": {"teacher_id": teacher_id}})


def get_class_students(db, teacher_id):
    """All students who joined this teacher's class."""
    rows = db[USERS].find({"role": "student", "teacher_id": teacher_id}, {"password_hash": 0})
    return [_with_id(r) for r in rows]


def get_prediction_summaries(db, user_ids):
    """For each user id: how many checks they made and their latest one."""
    pipeline = [
        {"$match": {"user_id": {"$in": list(user_ids)}}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}, "latest": {"$first": "$$ROOT"}}},
    ]
    return {row["_id"]: row for row in db[PREDICTIONS].aggregate(pipeline)}


# ---------------------------------------------------------------- students (CRUD)
def seed_students(db, df, teacher_id):
    """Insert exam records (owned by this teacher) from a DataFrame. Safe to run many times.

    $setOnInsert means: only write the document if that student_id does not
    exist yet for this teacher. Existing records (even edited ones) are left untouched.
    """
    operations = [
        UpdateOne({"teacher_id": teacher_id, "student_id": row["student_id"]},
                  {"$setOnInsert": {**row, "teacher_id": teacher_id}}, upsert=True)
        for row in df.to_dict("records")
    ]
    if not operations:
        return 0, 0
    result = db[STUDENTS].bulk_write(operations, ordered=False)
    inserted = result.upserted_count
    return inserted, len(operations) - inserted  # (new, already existed)


def claim_unowned_students(db, teacher_id):
    """Records made by an older version have no owner. Give them to this teacher."""
    return db[STUDENTS].update_many({"teacher_id": None}, {"$set": {"teacher_id": teacher_id}}).modified_count


def insert_student(db, student, teacher_id):
    """CREATE. Returns (True, message) or (False, message)."""
    try:
        db[STUDENTS].insert_one({**student, "teacher_id": teacher_id})
        return True, f"Record {student['student_id']} added."
    except DuplicateKeyError:
        return False, f"You already have a record with ID {student['student_id']}."
    except PyMongoError as error:
        return False, f"Database error: {error}"


def get_students(db, teacher_id):
    """READ this teacher's records (sorted by student_id). Internal fields are hidden."""
    try:
        return list(db[STUDENTS].find({"teacher_id": teacher_id}, {"_id": 0, "teacher_id": 0})
                    .sort("student_id", 1))
    except PyMongoError as error:
        raise DatabaseError(f"Could not read records: {error}")


def get_student(db, teacher_id, student_id):
    """READ one of this teacher's records, or None if not found."""
    return db[STUDENTS].find_one({"teacher_id": teacher_id, "student_id": student_id},
                                 {"_id": 0, "teacher_id": 0})


def get_training_records(db):
    """Every teacher's records, for training the shared forecast model.

    Only numbers are used. Two teachers may both have a record called S001, so the
    teacher id is added to the ID to keep every row separate.
    """
    rows = list(db[STUDENTS].find({}, {"_id": 0}))
    for row in rows:
        row["student_id"] = f"{row.pop('teacher_id', None)}:{row['student_id']}"
    return rows


def update_student(db, teacher_id, student_id, new_values):
    """UPDATE. Returns (True, message) or (False, message)."""
    try:
        result = db[STUDENTS].update_one({"teacher_id": teacher_id, "student_id": student_id},
                                         {"$set": new_values})
    except PyMongoError as error:
        return False, f"Database error: {error}"
    if result.matched_count == 0:
        return False, f"Record {student_id} was not found."
    return True, f"Record {student_id} updated."


def delete_student(db, teacher_id, student_id):
    """DELETE. Returns (True, message) or (False, message)."""
    try:
        result = db[STUDENTS].delete_one({"teacher_id": teacher_id, "student_id": student_id})
    except PyMongoError as error:
        return False, f"Database error: {error}"
    if result.deleted_count == 0:
        return False, f"Record {student_id} was not found."
    return True, f"Record {student_id} deleted."


# ---------------------------------------------------------------- evaluations
def save_evaluation(db, evaluation):
    """Save the metrics + model info of one training run."""
    document = dict(evaluation)  # copy, so the caller's dictionary is not changed
    document["created_at"] = _now()
    db[EVALUATIONS].insert_one(document)


def get_latest_evaluation(db):
    """Most recent evaluation document, or None."""
    return db[EVALUATIONS].find_one({}, {"_id": 0}, sort=[("created_at", -1)])


# ---------------------------------------------------------------- prediction history
def save_prediction(db, user_id, features, predicted_marks, pass_fail, pass_probability):
    """Save one prediction (who asked, inputs, and both model outputs)."""
    db[PREDICTIONS].insert_one(
        {
            "user_id": user_id,
            "study_hours": features["study_hours"],
            "attendance": features["attendance"],
            "previous_marks": features["previous_marks"],
            "predicted_marks": predicted_marks,
            "predicted_result": pass_fail,
            "pass_probability": pass_probability,
            "created_at": _now(),
        }
    )


def get_user_predictions(db, user_id, limit=30):
    """This user's latest predictions first. created_at is returned as text."""
    rows = list(db[PREDICTIONS].find({"user_id": user_id}, {"_id": 0, "user_id": 0})
                .sort("created_at", -1).limit(limit))
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
    return rows
