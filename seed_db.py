"""Load the sample data into MongoDB: past exam records, a demo teacher and a demo class.

Run:  python seed_db.py
Safe to run again and again: anything that already exists is skipped.
"""
from werkzeug.security import generate_password_hash

from src.database import (DatabaseError, claim_unowned_students, create_user, find_user_by_email,
                          get_db, save_prediction, seed_students)
from src.prediction import models_exist, predict_student
from src.preprocessing import clean_data, load_csv
from src.training import train_and_evaluate

DEMO_CLASS_CODE = "DEMO42"
TEACHER = {"name": "Demo Teacher", "email": "teacher@school.com", "password": "teacher123"}

# name, email, password, then the checks they made (study hours, attendance, last exam marks)
DEMO_STUDENTS = [
    ("Demo Student", "student@school.com", "student123", [(2, 65, 48), (3, 72, 52), (4, 80, 58)]),
    ("Ananya Verma", "ananya@school.com", "student123", [(5, 92, 72), (5.5, 94, 75)]),
    ("Rohan Mehta", "rohan@school.com", "student123", [(1, 55, 30), (1.5, 58, 32)]),
    ("Meera Nair", "meera@school.com", "student123", [(3, 70, 50)]),
    ("Arjun Singh", "arjun@school.com", "student123", [(0.5, 48, 35), (1, 52, 36), (1, 50, 38)]),
    ("Sneha Iyer", "sneha@school.com", "student123", [(4, 85, 64)]),
]


def seed_demo_class(db):
    """Create the demo teacher + students (linked together). Returns how many students were new."""
    if not models_exist():
        train_and_evaluate()  # forecasts are needed to create the demo history

    ok, _ = create_user(db, TEACHER["name"], TEACHER["email"],
                        generate_password_hash(TEACHER["password"]), "teacher", DEMO_CLASS_CODE)
    teacher = find_user_by_email(db, TEACHER["email"])
    if not teacher.get("class_code"):  # demo teacher made by an older version of this project
        db["users"].update_one({"email": TEACHER["email"]}, {"$set": {"class_code": DEMO_CLASS_CODE}})

    created = 0
    for name, email, password, checks in DEMO_STUDENTS:
        ok, user = create_user(db, name, email, generate_password_hash(password),
                               "student", teacher_id=teacher["id"])
        if ok:
            created += 1
            for hours, attendance, previous in checks:
                result = predict_student(hours, attendance, previous)
                save_prediction(db, user["id"],
                                {"study_hours": hours, "attendance": attendance, "previous_marks": previous},
                                result["predicted_marks"], result["result"], result["pass_probability"])
        else:  # already there: make sure it is linked to the demo teacher
            db["users"].update_one({"email": email, "teacher_id": {"$exists": False}},
                                   {"$set": {"teacher_id": teacher["id"]}})
    return created


def seed_everything(db):
    """Demo teacher + class, and the 300 sample exam records (owned by the demo teacher)."""
    df, _ = clean_data(load_csv())
    created = seed_demo_class(db)
    teacher = find_user_by_email(db, TEACHER["email"])
    claimed = claim_unowned_students(db, teacher["id"])  # records from an older version
    new, skipped = seed_students(db, df, teacher["id"])
    return {"records_new": new, "records_existing": skipped, "records_claimed": claimed,
            "students_created": created}


def main():
    df, report = clean_data(load_csv())
    print(f"CSV rows: {report['rows_in_file']}, valid rows: {report['rows_after_cleaning']}")

    try:
        db = get_db()
    except DatabaseError as error:
        print(f"\nERROR: {error}")
        raise SystemExit(1)

    result = seed_everything(db)
    print(f"Sample exam records (owned by the demo teacher) - new: {result['records_new']}, "
          f"already there: {result['records_existing']}, adopted from an older version: {result['records_claimed']}")
    print(f"Demo class students created: {result['students_created']}")

    print("\nLog in with (password in brackets):")
    print(f"  teacher  {TEACHER['email']}  [{TEACHER['password']}]   class code: {DEMO_CLASS_CODE}")
    print(f"  student  student@school.com  [student123]   (also ananya@, rohan@, meera@, arjun@, sneha@school.com)")


if __name__ == "__main__":
    main()
