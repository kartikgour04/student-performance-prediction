"""Creates data/students.csv with SYNTHETIC (computer-generated) student data.

Run from the project folder:  python data/generate_sample_data.py

The data is NOT real. Exam marks depend loosely on previous marks, study hours
and attendance, plus random noise, so the models have something to learn but
the answer is never perfectly predictable.
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)  # fixed seed -> same file every time
N = 300

previous_marks = np.clip(rng.normal(58, 17, N), 10, 98)
study_hours = np.clip(rng.gamma(shape=3.0, scale=1.0, size=N), 0.3, 9.0)
attendance = np.clip(rng.normal(70 + 0.15 * (previous_marks - 58), 12, N), 40, 100)
noise = rng.normal(0, 7, N)

exam_marks = 0.55 * previous_marks + 3.2 * study_hours + 0.18 * attendance - 4 + noise
exam_marks = np.clip(exam_marks, 0, 100)

df = pd.DataFrame(
    {
        "student_id": [f"S{i:03d}" for i in range(1, N + 1)],
        "study_hours": study_hours.round(1),
        "attendance": attendance.round(1),
        "previous_marks": previous_marks.round(1),
        "exam_marks": exam_marks.round(1),
    }
)

out_file = Path(__file__).parent / "students.csv"
df.to_csv(out_file, index=False)
print(f"Saved {len(df)} rows to {out_file}")
print(f"Pass (>=40): {(df.exam_marks >= 40).sum()}  Fail (<40): {(df.exam_marks < 40).sum()}")
