"""Train and evaluate both models, then save them to the models/ folder."""
import json

import joblib
import sklearn
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluation import evaluate_classification, evaluate_regression
from src.preprocessing import (
    FEATURES,
    PASS_MARK,
    PROJECT_FOLDER,
    RANDOM_STATE,
    TEST_SIZE,
    clean_data,
    load_csv,
    split_data,
)

MODEL_FOLDER = PROJECT_FOLDER / "models"
LINEAR_MODEL_FILE = MODEL_FOLDER / "linear_regression.joblib"
LOGISTIC_MODEL_FILE = MODEL_FOLDER / "logistic_regression.joblib"
METRICS_FILE = MODEL_FOLDER / "latest_evaluation.json"  # backup copy of the results


def train_and_evaluate(df=None, dataset_name="data/students.csv (synthetic sample data)"):
    """Returns a dictionary with all metrics and model information.

    df=None  -> train from the CSV file (python train_models.py)
    df given -> train from that data (the teacher's Retrain button passes the MongoDB students)
    """
    df, cleaning_report = clean_data(load_csv() if df is None else df)
    X_train, X_test, marks_train, marks_test, pass_train, pass_test = split_data(df)

    # Model 1: Linear Regression -> predicts marks.
    # No scaling: its predictions do not change if features are scaled.
    linear_model = LinearRegression()
    linear_model.fit(X_train, marks_train)
    marks_pred = linear_model.predict(X_test).clip(0, 100)  # marks cannot be outside 0-100

    # Model 2: Logistic Regression -> predicts Pass (1) / Fail (0).
    # StandardScaler puts the 3 features on a similar scale so the solver converges well.
    # It is inside a pipeline, so it is fitted on training data only (no leakage).
    logistic_model = make_pipeline(
        StandardScaler(),
        LogisticRegression(random_state=RANDOM_STATE),
    )
    logistic_model.fit(X_train, pass_train)
    pass_pred = logistic_model.predict(X_test)

    classification = evaluate_classification(pass_test, pass_pred)
    regression = evaluate_regression(marks_test, marks_pred)

    MODEL_FOLDER.mkdir(exist_ok=True)
    joblib.dump(linear_model, LINEAR_MODEL_FILE)
    joblib.dump(logistic_model, LOGISTIC_MODEL_FILE)

    evaluation = {
        "dataset": dataset_name,
        "cleaning_report": cleaning_report,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "features": FEATURES,
        "pass_mark": PASS_MARK,
        "positive_class": "Pass (1)",
        "scikit_learn_version": sklearn.__version__,
        "linear_regression": {
            **regression,
            "intercept": float(linear_model.intercept_),
            "coefficients": {f: float(c) for f, c in zip(FEATURES, linear_model.coef_)},
        },
        "logistic_regression": classification,
        # actual vs predicted values of the test set (used by the Visualizations page)
        "test_results": {
            "actual_marks": [float(v) for v in marks_test],
            "predicted_marks": [round(float(v), 2) for v in marks_pred],
        },
    }
    METRICS_FILE.write_text(json.dumps(evaluation, indent=2))
    return evaluation
