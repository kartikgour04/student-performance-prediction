"""Use the saved models to predict, and turn the result into friendly advice."""
import joblib
import pandas as pd

from src.preprocessing import FEATURES
from src.training import LINEAR_MODEL_FILE, LOGISTIC_MODEL_FILE

_models = {}  # the models are loaded from disk once and then kept in memory


def models_exist():
    return LINEAR_MODEL_FILE.exists() and LOGISTIC_MODEL_FILE.exists()


def reload_models():
    """Forget the cached models (called after retraining)."""
    _models.clear()


def _load():
    if not models_exist():
        raise FileNotFoundError("Models not found. Run:  python train_models.py")
    if not _models:
        _models["linear"] = joblib.load(LINEAR_MODEL_FILE)
        _models["logistic"] = joblib.load(LOGISTIC_MODEL_FILE)
    return _models["linear"], _models["logistic"]


def _marks(linear_model, study_hours, attendance, previous_marks):
    row = pd.DataFrame([[study_hours, attendance, previous_marks]], columns=FEATURES)
    return float(min(max(linear_model.predict(row)[0], 0), 100))


def predict_student(study_hours, attendance, previous_marks):
    """Returns predicted marks (0-100), Pass/Fail text and the Pass probability."""
    linear_model, logistic_model = _load()
    # same column names and order as in training
    row = pd.DataFrame([[study_hours, attendance, previous_marks]], columns=FEATURES)
    return {
        "predicted_marks": round(_marks(linear_model, study_hours, attendance, previous_marks), 1),
        "result": "Pass" if logistic_model.predict(row)[0] == 1 else "Fail",
        "pass_probability": round(float(logistic_model.predict_proba(row)[0][1]), 4),
    }


def predict_many(df):
    """Predict for many students at once (teacher panel). Needs the 3 feature columns."""
    linear_model, logistic_model = _load()
    X = df[FEATURES]
    return pd.DataFrame({
        "predicted_marks": linear_model.predict(X).clip(0, 100).round(1),
        "pass_probability": logistic_model.predict_proba(X)[:, 1].round(4),
    }, index=df.index)


def level_for(pass_probability):
    """great / ok / risk, used for colours and for finding students who need support."""
    if pass_probability >= 0.85:
        return "great"
    return "ok" if pass_probability >= 0.5 else "risk"


HEADLINES = {
    "great": "You're on track. Keep it up!",
    "ok": "You're likely to pass, with room to improve.",
    "risk": "You may struggle. A few changes can help.",
}


def advice_for(study_hours, attendance, previous_marks, prediction):
    """Friendly headline + tips. Tips come from 'what if' predictions of the same model."""
    level = level_for(prediction["pass_probability"])
    headline = HEADLINES[level]

    linear_model, _ = _load()
    base = _marks(linear_model, study_hours, attendance, previous_marks)
    tips = []

    if study_hours < 10:
        gain = _marks(linear_model, study_hours + 1, attendance, previous_marks) - base
        if gain >= 0.5:
            tips.append(f"Studying 1 more hour a day could add about {gain:.1f} marks.")
    if attendance < 95:
        better = min(100, attendance + 10)
        gain = _marks(linear_model, study_hours, better, previous_marks) - base
        if gain >= 0.5:
            tips.append(f"Raising attendance to {better:.0f}% could add about {gain:.1f} marks.")
    if study_hours < 1:
        tips.append("Even 30 to 60 minutes of focused study a day makes a difference.")
    if level == "risk":
        tips.append("Talk to your teacher early. Asking for help sooner works better.")
    if not tips:
        tips.append("Keep your routine steady. Consistency matters most.")
    return {"level": level, "headline": headline, "tips": tips}
