"""Loading, cleaning, validating and splitting the data."""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_FOLDER / "data" / "students.csv"

FEATURES = ["study_hours", "attendance", "previous_marks"]  # inputs (X)
TARGET_MARKS = "exam_marks"                                   # target of Linear Regression
PASS_MARK = 40                                                # Pass = exam_marks >= 40
RANDOM_STATE = 42
TEST_SIZE = 0.2

# Allowed range for every numeric column
RANGES = {
    "study_hours": (0, 24),   # hours per day
    "attendance": (0, 100),   # percent
    "previous_marks": (0, 100),
    "exam_marks": (0, 100),
}


def load_csv(path=DATA_FILE):
    """Step 1: read the CSV file with pandas."""
    return pd.read_csv(path)


def clean_data(df):
    """Steps 2-4: check missing values, remove invalid rows, validate ranges.

    Returns (clean_dataframe, report_dictionary).
    """
    columns = ["student_id"] + FEATURES + [TARGET_MARKS]
    missing_columns = [c for c in columns if c not in df.columns]
    if missing_columns:
        raise ValueError(f"The CSV is missing these columns: {missing_columns}")

    report = {"rows_in_file": len(df)}
    df = df[columns].copy()

    # make sure numbers are numbers (bad text becomes NaN)
    for column in FEATURES + [TARGET_MARKS]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    report["missing_values"] = int(df.isna().sum().sum())
    df = df.dropna()

    before = len(df)
    df = df.drop_duplicates(subset="student_id", keep="first")
    report["duplicate_ids_removed"] = before - len(df)

    before = len(df)
    for column, (low, high) in RANGES.items():
        df = df[df[column].between(low, high)]
    report["out_of_range_removed"] = before - len(df)

    df = df.reset_index(drop=True)
    report["rows_after_cleaning"] = len(df)
    if df.empty:
        raise ValueError("No valid rows left after cleaning. Check data/students.csv.")
    return df, report


def make_pass_label(marks):
    """1 = Pass (marks >= 40), 0 = Fail (marks < 40)."""
    return (marks >= PASS_MARK).astype(int)


def split_data(df):
    """Step 5: one train/test split used by BOTH models.

    * X contains only study_hours, attendance, previous_marks.
      exam_marks is NOT in X, so there is no data leakage.
    * stratify keeps the same Pass/Fail share in train and test sets.
    * random_state=42 makes the split identical on every run.
    """
    X = df[FEATURES]
    y_marks = df[TARGET_MARKS]
    y_pass = make_pass_label(y_marks)

    if y_pass.nunique() < 2:
        raise ValueError("The data needs both Pass and Fail students to train the classifier.")
    if y_pass.value_counts().min() < 2:
        raise ValueError("Need at least 2 Pass and 2 Fail students to split the data.")

    return train_test_split(
        X, y_marks, y_pass,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_pass,
    )


# Names shown to people instead of column names
LABELS = {
    "study_hours": "Study time",
    "attendance": "Attendance",
    "previous_marks": "Last exam marks",
    "exam_marks": "Exam marks",
}


def validate_inputs(study_hours, attendance, previous_marks):
    """Check values typed by the user. Returns a list of error messages (empty = OK)."""
    errors = []
    values = {"study_hours": study_hours, "attendance": attendance, "previous_marks": previous_marks}
    for name, value in values.items():
        low, high = RANGES[name]
        if value is None:
            errors.append(f"{LABELS[name]} is required.")
        elif not low <= value <= high:
            errors.append(f"{LABELS[name]} must be between {low} and {high}.")
    return errors


def validate_student(student_id, study_hours, attendance, previous_marks, exam_marks):
    """Same as validate_inputs, plus student_id and exam_marks (for Add/Update)."""
    errors = []
    if not student_id or not str(student_id).strip():
        errors.append("Student ID is required.")
    errors += validate_inputs(study_hours, attendance, previous_marks)
    low, high = RANGES["exam_marks"]
    if exam_marks is None:
        errors.append("Exam marks is required.")
    elif not low <= exam_marks <= high:
        errors.append(f"Exam marks must be between {low} and {high}.")
    return errors
