# Student Performance Prediction System using MongoDB, PyMongo and Machine Learning

**Project Report**

| | |
|---|---|
| Student name | ______________________ |
| Roll number | ______________________ |
| Course / Semester | ______________________ |
| Guide / Teacher | ______________________ |
| College | ______________________ |
| Date | ______________________ |

---

## 1. Title

Student Performance Prediction System using MongoDB, PyMongo and Machine Learning

## 2. Abstract

This project builds a small system that predicts how a student may perform in an exam. It uses three pieces of information about a student: **study hours per day**, **attendance percentage** and **previous exam marks**. Two Machine Learning models are used. **Linear Regression** predicts the expected exam marks. **Logistic Regression** predicts whether the student will Pass (marks 40 or more) or Fail (marks below 40). Student records, prediction history and model evaluation results are stored in a **MongoDB** database using the **PyMongo** library. A **Flask** website (backend) with an HTML/CSS/JavaScript frontend lets students sign up, log in, check their expected marks and chance of passing with personal tips, and keep a history of their checks. A teacher panel lets teachers manage student records, see class charts, find students who may need support, and view the evaluation results. The models are evaluated on unseen test data using six metrics: Accuracy, Precision, Recall, F1 Score (for classification) and R² Score and Mean Absolute Error (for regression). The sample dataset is **synthetic** (computer-generated), so the results show how the system works but do not describe real students.

## 3. Introduction

Teachers often want to know early which students may struggle. Machine Learning (ML) is a way of letting a computer learn patterns from past data and use them to make predictions about new data.

A **database** stores data safely so it can be searched and changed later. **MongoDB** is a popular NoSQL database. Instead of tables and rows, it stores *documents* (similar to Python dictionaries) inside *collections*. **PyMongo** is the official Python library used to talk to MongoDB.

This project joins both ideas: MongoDB stores the data and results, and ML models make predictions.

## 4. Problem Statement

**The real-life problem.** In schools and colleges, most students find out that they are struggling only when the exam results are announced. By then it is too late to improve. The problem has two sides:

1. **Students are guessing.** A student rarely knows how daily habits, such as hours of study and class attendance, connect to the likely exam result. Without that link, a student cannot tell whether the current effort is enough.
2. **Teachers cannot watch everyone.** A teacher with a large class cannot closely track every student, so students who are slipping are noticed late, or not at all. Support given after a failed exam helps far less than support given weeks earlier.

**Problem statement.** To design and build a web-based early-warning and self-check system in which:

* a **student** enters study hours per day, attendance and previous exam marks, and receives an expected exam mark, a chance of passing, and simple tips on what could improve the result;
* a **teacher** creates an account, receives a unique **class code**, and sees only the students who joined with that code, with those who may need support listed first;
* all accounts, records, forecasts and evaluation results are stored in MongoDB, and the forecasts are produced by two Machine Learning models (Linear Regression for marks, Logistic Regression for Pass/Fail) that are measured with six standard metrics.

**Who benefits.** Students get an early, personal signal to adjust their habits. Teachers get a short list of students to talk to before the exam, instead of after it.

**Important note.** The forecasts are estimates from a model trained on synthetic sample data. They are meant to start a conversation between a student and a teacher, not to judge a student or make decisions about them.

## 5. Project Objectives

1. Store student records in MongoDB using PyMongo.
2. Perform Create, Read, Update and Delete (CRUD) operations on the records.
3. Clean and validate the data before using it.
4. Train a Linear Regression model to predict exam marks.
5. Train a Logistic Regression model to predict Pass/Fail.
6. Evaluate the models using Accuracy, Precision, Recall, F1 Score, R² Score and MAE.
7. Save prediction history and evaluation results in MongoDB.
8. Build a real website with a Flask backend and a simple frontend, with separate student and teacher accounts, for all of the above.
9. Let each teacher get a class code, let students join with it, and show each teacher only their own students.
10. Protect the website with login, hashed passwords and role checks (a teacher access code is needed to create a teacher account).

## 6. Scope and Limitations

**Scope:** a small educational project using three input features, two simple models and one database, running on a personal computer.

**Limitations:** see Section 18. In short: the data is synthetic, only three features are used, and predictions are estimates only.

## 7. Dataset Description

* File: `data/students.csv` — **300 student records**.
* The data is **synthetic**: it was created by the script `data/generate_sample_data.py` using a fixed random seed. It is **not real student data**.
* Exam marks were generated from previous marks, study hours and attendance **plus random noise**. The noise means the answer cannot be predicted perfectly, which is more realistic than a fixed rule.
* The data contains both Pass and Fail students (run `python data/generate_sample_data.py` to see the counts).

| Column | Meaning | Allowed range |
|---|---|---|
| `student_id` | Unique ID such as S001 | text, must be unique |
| `study_hours` | Hours studied per day | 0 – 24 |
| `attendance` | Attendance percentage | 0 – 100 |
| `previous_marks` | Marks in the previous exam | 0 – 100 |
| `exam_marks` | Marks in the exam (target for prediction) | 0 – 100 |

**Pass/Fail rule:** Pass = `exam_marks >= 40`, Fail = `exam_marks < 40`.

Because the data is synthetic, results may not generalize to real students.

## 8. Technology Stack

| Tool | Use (in simple words) |
|---|---|
| Python | The programming language |
| MongoDB | The database that stores the data |
| PyMongo | Python library to use MongoDB |
| pandas | Reads the CSV file and handles tables of data |
| scikit-learn | Provides the ML models, train/test split and the metrics |
| Flask | The backend: serves the pages and the JSON API, handles login and prediction requests |
| HTML, CSS, JavaScript | The frontend that the user sees in the browser (no framework) |
| Chart.js | Draws the charts in the browser |
| werkzeug | Safely hashes passwords (comes with Flask) |
| python-dotenv | Reads the secret database address from the `.env` file |
| joblib | Saves and loads the trained models |

## 9. MongoDB and PyMongo Implementation

**Database:** `student_performance_db`

| Collection | What it stores |
|---|---|
| `users` | Website accounts: name, email (unique), hashed password, role (student or teacher). A teacher also has a unique `class_code`; a student who joined a class has a `teacher_id` |
| `students` | One document per exam record. It stores the `teacher_id` of its owner; the pair (`teacher_id`, `student_id`) is unique |
| `model_evaluations` | Metrics and model information from each training run |
| `predictions` | History of the forecasts each user made on the website |

A student document looks like this:

```json
{ "student_id": "S001", "study_hours": 6.6, "attendance": 75.5,
  "previous_marks": 63.2, "exam_marks": 56.2 }
```

Key points (all in `src/database.py`):

* **Connection:** `MongoClient(uri)` with the address read from `.env` (never written in the code). A `ping` command checks that the server really responds. If it does not, a friendly `DatabaseError` is shown instead of a long error.
* **Unique constraint:** `create_index("student_id", unique=True)` — MongoDB refuses two students with the same ID. The code catches `DuplicateKeyError` and shows "Student ID already exists".
* **CRUD:**
  * Create → `insert_one`
  * Read → `find` / `find_one`
  * Update → `update_one` with `$set`
  * Delete → `delete_one`
* **Safe seeding:** `seed_db.py` uses `bulk_write` with `UpdateOne(..., upsert=True)` and `$setOnInsert`. This means "insert only if this student_id does not exist", so running it many times never creates duplicates and never overwrites edited records.
* **Evaluation results** are saved with `insert_one` in `model_evaluations`, and the teacher panel reads the newest one.
* **Prediction history** is saved with `insert_one` in `predictions`.

## 10. System Architecture

```
 data/students.csv
        |
        |  python seed_db.py                 python train_models.py
        v                                           |
 +-----------------+                                v
 |    MongoDB      |        +----------------------------------------+
 |  users          |        | preprocessing.py : load, clean, split  |
 |  students       | <------| training.py      : train 2 models      |
 |  predictions    |  save  | evaluation.py    : 6 metrics           |
 |  model_evaluat. | results| prediction.py    : forecast + tips     |
 +--------+--------+        +----------------------------------------+
          ^                                  |
          |  PyMongo                         | saved models (models/*.joblib)
          v                                  v
 +----------------------------------------------------+
 |   Backend: Flask (app.py)  - pages + JSON API      |
 |   login, roles, /api/predict, /api/admin/...       |
 +----------------------------------------------------+
                         ^
                         |  HTTP requests (fetch)
                         v
 +----------------------------------------------------+
 |   Frontend: HTML + CSS + JavaScript (in browser)   |
 |   Student: forecast, progress | Teacher: panel     |
 +----------------------------------------------------+
```

**Flow:** the CSV is loaded into MongoDB with `seed_db.py`. Training reads the CSV, trains and evaluates both models, saves the models to the `models/` folder and the results to MongoDB. When a user opens the website, the browser (frontend) sends requests to the Flask backend. The backend checks the login, loads the saved models to predict, and reads or writes MongoDB. A teacher can retrain the models from the latest exam records with one button.

**Teacher and student link.** A teacher account can only be created with a secret *teacher access code* kept in the `.env` file. Each teacher receives a random 6-character *class code*. A student enters the class code when signing up (or later on the dashboard), and the student's account then stores that teacher's ID. The teacher panel only queries students with that teacher ID, and the history route re-checks this, so one teacher can never open another teacher's students. Exam records are separated in the same way: every record stores the `teacher_id` of its owner, every read, update and delete includes that ID, and the unique index is on (`teacher_id`, `student_id`) so two teachers can use the same student ID. The Machine Learning models are shared: when a teacher presses "Update forecasts", they learn from the numbers in all teachers' records, but no teacher can see another teacher's rows. The student is told on screen that their teacher can see their forecasts.

## 11. Data Preprocessing

Preprocessing means preparing raw data so the models can use it. Done in `src/preprocessing.py`:

1. **Load the CSV** with `pandas.read_csv`.
2. **Check missing values.** Numbers are converted with `pd.to_numeric`; bad text becomes empty (NaN). Rows with any missing value are removed and counted.
3. **Remove duplicates.** If a `student_id` appears twice, only the first row is kept.
4. **Validate ranges.** Study hours must be 0–24; attendance, previous marks and exam marks must be 0–100. Rows outside these ranges are removed.
5. **Empty data check.** If nothing valid remains, a clear error is shown.
6. **Select features and targets.**
   * Inputs (X): `study_hours`, `attendance`, `previous_marks`
   * Target 1 (Linear Regression): `exam_marks`
   * Target 2 (Logistic Regression): `pass_fail` = 1 if `exam_marks >= 40`, else 0
7. **Train/test split:** 80% for training and 20% for testing, `random_state=42` (so the split is the same every time), and `stratify` so Pass and Fail are in the same proportion in both parts. **The same split is used for both models.**
8. **Scaling:** `StandardScaler` is used **only for Logistic Regression**, because it works best when all inputs are on a similar scale (hours are 0–9 but marks go up to 100). It is placed inside a scikit-learn *pipeline* so it learns its values from the training data only. Linear Regression is **not** scaled because scaling does not change its predictions.

**Avoiding data leakage:** *Data leakage* means accidentally giving the model the answer. `exam_marks` is the target, so it is **never** used as an input. Only study hours, attendance and previous marks are inputs. The test data is never used for training.

## 12. Linear Regression Implementation

**What it does:** finds the straight-line (here, flat "plane") relationship between the inputs and the marks:

`predicted_marks = intercept + a × study_hours + b × attendance + c × previous_marks`

The numbers a, b and c (coefficients) are learned from the training data. The Model Evaluation page shows them.

**Code idea (`src/training.py`):**

```python
linear_model = LinearRegression()
linear_model.fit(X_train, marks_train)
marks_pred = linear_model.predict(X_test).clip(0, 100)
```

`clip(0, 100)` keeps predicted marks inside the possible range. The output is **predicted exam marks**. It is evaluated using **R² Score** and **MAE**.

## 13. Logistic Regression Implementation

**What it does:** despite its name, Logistic Regression is used for **classification**. It calculates the **probability** that a student passes (a number from 0 to 1). If the probability is 0.5 or more, the prediction is **Pass**; otherwise **Fail**.

**Code idea (`src/training.py`):**

```python
logistic_model = make_pipeline(StandardScaler(), LogisticRegression(random_state=42))
logistic_model.fit(X_train, pass_train)
pass_pred = logistic_model.predict(X_test)
```

**Assumptions:** Pass = marks ≥ 40; the three inputs are enough to estimate the chance of passing; the pattern in the data stays the same for new students. The positive class is **Pass (1)**, so Precision, Recall and F1 are calculated for Pass. It is evaluated using **Accuracy, Precision, Recall and F1 Score**.

**Note:** the two models are trained separately. Near the pass mark (40), the predicted marks might be, for example, 41 while the classifier says Fail. This is normal and is mentioned in the dashboard.

## 14. Evaluation Metrics — Formulas and Easy Examples

Evaluation is always done on the **test set** — data the model has never seen.

### 14.1 Classification metrics (Logistic Regression)

First count four things (the *confusion matrix*), with **Pass as the positive class**:

| | Predicted Pass | Predicted Fail |
|---|---|---|
| **Actually Pass** | TP (True Positive) | FN (False Negative) |
| **Actually Fail** | FP (False Positive) | TN (True Negative) |

**Easy example (invented only to explain formulas, NOT project results):** 15 test students: TP = 8, FN = 2, FP = 1, TN = 4.

| Metric | Meaning in simple words | Formula | Example |
|---|---|---|---|
| **Accuracy** | Out of all students, how many predictions were correct? | (TP + TN) / (TP + TN + FP + FN) | (8 + 4) / 15 = **0.80** |
| **Precision** | When the model says "Pass", how often is it right? | TP / (TP + FP) | 8 / 9 = **0.889** |
| **Recall** | Out of students who really passed, how many did the model find? | TP / (TP + FN) | 8 / 10 = **0.80** |
| **F1 Score** | One number that balances Precision and Recall | 2 × (Precision × Recall) / (Precision + Recall) | 2 × 0.889 × 0.80 / (0.889 + 0.80) = **0.842** |

Why more than accuracy? If 90 of 100 students pass, a lazy model that always says "Pass" gets 90% accuracy but never finds a failing student. Precision, Recall and F1 show these problems.

`zero_division=0` is used: if the model never predicts Pass, Precision would be 0/0, so it is set to 0 instead of crashing.

### 14.2 Regression metrics (Linear Regression)

These compare the predicted marks with the actual marks.

**Easy example (invented):** actual marks = 50, 60, 70, 40; predicted = 55, 58, 66, 45.

| Metric | Meaning in simple words | Formula | Example |
|---|---|---|---|
| **MAE** (Mean Absolute Error) | On average, how many marks is the prediction wrong by? Lower is better. | average of &#124;actual − predicted&#124; | errors 5, 2, 4, 5 → 16 / 4 = **4.0 marks** |
| **R² Score** | How much of the ups and downs in marks the model explains. 1 = perfect, 0 = no better than always guessing the average. | 1 − (SS_res / SS_tot) | mean actual = 55; SS_tot = 500; SS_res = 70; 1 − 70/500 = **0.86** |

Here SS_res = sum of (actual − predicted)² and SS_tot = sum of (actual − mean of actual)².

**Important:** Accuracy, Precision, Recall and F1 are **classification** metrics (Pass/Fail). R² and MAE are **regression** metrics (marks). They are never mixed in this project.

## 15. Actual Evaluation Results

The real results are **not typed into this report**. They are calculated by the code, because scores depend on the dataset and the train/test split. To get your real results:

```bash
python train_models.py
```

This prints all six metrics, saves them in MongoDB and writes them as ready-made tables to **`docs/results_summary.md`**. Copy the numbers into the table below. You can also open the **Forecast quality** tab of the teacher panel.

| Model | Metric | Value (from your run) |
|---|---|---|
| Logistic Regression | Accuracy | ________ |
| Logistic Regression | Precision (positive class = Pass) | ________ |
| Logistic Regression | Recall (positive class = Pass) | ________ |
| Logistic Regression | F1 Score (positive class = Pass) | ________ |
| Linear Regression | R² Score | ________ |
| Linear Regression | MAE (marks) | ________ |

Confusion matrix on the test set: TP = ____, TN = ____, FP = ____, FN = ____ (also printed by the script).

## 16. Results and Discussion

*(Write this after you have your real numbers. Use the guide below.)*

* **Accuracy:** say what fraction of test students were classified correctly.
* **Precision and Recall:** say whether the model is better at avoiding false "Pass" predictions (Precision) or at finding all passing students (Recall). Compare them using the confusion matrix.
* **F1 Score:** summarizes the balance of the two.
* **R² Score:** a value closer to 1 means the model explains more of the variation in marks. Because noise was added to the synthetic data, a perfect 1.0 is not expected.
* **MAE:** say that, on average, predicted marks are about this many marks away from the actual marks.
* **Forecast vs real marks plot:** dots close to the dashed line mean good predictions.
* **Coefficients:** the Model Evaluation page shows how many marks each input adds. This shows which input the model relies on most **within this synthetic dataset**.
* **Remember:** the dataset is synthetic. These results show that the system works, not how real students behave. Scores will change if the data or the split changes.

## 17. Screenshots Checklist

Take these screenshots after running the project and add them to your report (log in with the demo accounts from the README):

- [ ] Terminal: `python seed_db.py` output
- [ ] Terminal: `python train_models.py` output with the six metrics
- [ ] MongoDB Compass (or Atlas): `student_performance_db` with the three collections
- [ ] MongoDB Compass: `students` collection showing documents
- [ ] MongoDB Compass: `model_evaluations` document
- [ ] Website: Home page
- [ ] Website: Sign up page and Log in page
- [ ] Student dashboard with a forecast result and tips
- [ ] Student dashboard: progress chart and recent checks
- [ ] Sign up page in teacher mode (access code field)
- [ ] Teacher panel: My class (class code, statistics, students who need support first)
- [ ] Teacher panel: a student's History popup
- [ ] Student dashboard: "You are in ...'s class" banner and the Join class form
- [ ] Teacher panel: Exam records tab (charts, search, add, edit, delete)
- [ ] Teacher panel: Forecast quality tab with all six metrics
- [ ] Error message example (wrong password or invalid value)

## 18. Limitations

1. The dataset is **synthetic**; results may not generalize to real students.
2. Only three input features are used. Real performance depends on many more factors.
3. Linear and Logistic Regression assume simple, mostly straight-line relationships.
4. The dataset is small (300 records), so scores can change a lot with a different split.
5. Predictions are estimates, **not guarantees**, and must not be used for real decisions about students.
6. Models are trained from the CSV file. Records added or edited by teachers do not retrain the models automatically; a teacher must press the "Update forecasts" button (or run `python train_models.py`).
7. Teachers can see the forecasts of students who joined their class. This is shown to students on screen, but a real deployment would also need the school's data-protection rules and consent.
8. Login is basic (email and password with hashed passwords). There is no email verification, password reset or rate limiting, so the website is for local demonstration and is not ready for public deployment without more security work.

## 19. Future Enhancements

* Use real (anonymised and permitted) student data.
* Add more features such as assignments, family support or sleep.
* Try other models (Decision Tree, Random Forest) and compare them.
* Use cross-validation for more stable scores.
* Add a "Retrain model from MongoDB data" button.
* Add email verification, password reset and login rate limiting.
* Let teachers record each student's real exam marks so the forecasts learn from real results.
* Let a student leave a class, and let a teacher remove a student.
* Deploy the website online (with HTTPS and a production server).

## 20. Conclusion

The project shows how a database and Machine Learning can work together. MongoDB, accessed through PyMongo, stores student records, prediction history and evaluation results. Linear Regression predicts exam marks and Logistic Regression predicts Pass/Fail, both trained on a reproducible train/test split without data leakage. All six required metrics are calculated from real model output and shown in the teacher panel of a Flask website. Students use the same website to check their expected marks and receive personal tips. The system is simple and educational; with real data and more features it could be extended further.

## 21. References

1. MongoDB Documentation — https://www.mongodb.com/docs/
2. PyMongo Documentation — https://pymongo.readthedocs.io/
3. scikit-learn User Guide (LinearRegression, LogisticRegression, metrics) — https://scikit-learn.org/stable/user_guide.html
4. pandas Documentation — https://pandas.pydata.org/docs/
5. Flask Documentation — https://flask.palletsprojects.com/
6. Chart.js Documentation — https://www.chartjs.org/docs/
7. Dataset: synthetic, generated by `data/generate_sample_data.py` (no external dataset used).
