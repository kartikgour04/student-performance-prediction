"""The six evaluation metrics, calculated with scikit-learn.

Classification metrics (Logistic Regression) -> use the 0/1 Pass/Fail labels
Regression metrics   (Linear Regression)     -> use the real marks (0-100)
Never mix them: R2 and MAE are NOT calculated on Pass/Fail labels.
"""
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
)

POSITIVE_CLASS = 1  # 1 = Pass. Precision, Recall and F1 are calculated for "Pass".


def evaluate_classification(y_true, y_pred):
    """Accuracy, Precision, Recall, F1 for the Pass/Fail model."""
    # zero_division=0 -> if the model never predicts "Pass", precision becomes 0 (no crash)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=POSITIVE_CLASS, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=POSITIVE_CLASS, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, pos_label=POSITIVE_CLASS, zero_division=0)),
        "confusion_matrix": {
            "true_negative": int(tn),   # Fail predicted as Fail
            "false_positive": int(fp),  # Fail predicted as Pass
            "false_negative": int(fn),  # Pass predicted as Fail
            "true_positive": int(tp),   # Pass predicted as Pass
        },
    }


def evaluate_regression(y_true_marks, y_pred_marks):
    """R2 score and MAE for the marks model."""
    return {
        "r2_score": float(r2_score(y_true_marks, y_pred_marks)),
        "mae": float(mean_absolute_error(y_true_marks, y_pred_marks)),
    }
