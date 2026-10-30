# StudyPulse - Student Performance Prediction Website

A real website built with a **Flask backend**, an **HTML/CSS/JavaScript frontend**, **MongoDB (PyMongo)** and **Machine Learning**.

## The problem it solves

Most students find out they are struggling only when the results arrive, which is too late to change anything. Students don't know how their study time and attendance affect their result, and a teacher with a big class can't watch every student. StudyPulse is an **early-warning and self-check website**.

**Students** sign up, enter their study hours, attendance and last exam marks, and get their expected exam marks, their chance of passing and personal tips. Every check is saved so they can watch their progress.

**Teachers** create an account and get a unique **class code**. Exam records are private too: each teacher sees and edits only the records they added. Students join with that code, and the teacher sees **only their own students**, with those who need support listed first and each student's check history. Teachers also manage the exam records the forecasts learn from, see the forecast quality (Accuracy, Precision, Recall, F1, R², MAE), and can retrain the forecasts with one button.

- **Linear Regression** predicts exam marks.
- **Logistic Regression** predicts Pass (marks >= 40) or Fail.

> The sample dataset (`data/students.csv`) is **synthetic** (computer-generated). Results may not apply to real students, and forecasts must not be used for real decisions about students.

## Project structure

```
student_performance_project/
├── app.py                  # BACKEND: Flask server (pages + JSON API + login)
├── seed_db.py              # loads sample students + 2 demo accounts into MongoDB
├── train_models.py         # trains both models and calculates the 6 metrics
├── requirements.txt
├── .env.example            # copy to .env
├── templates/              # FRONTEND pages (HTML)
│   ├── base.html  index.html  login.html  register.html
│   └── dashboard.html (students)   admin.html (teachers)
├── static/
│   ├── css/style.css       # all styling
│   └── js/                 # FRONTEND logic: common.js auth.js dashboard.js admin.js
│                           #   chart.umd.js (Chart.js, included so it works offline)
├── src/                    # backend logic
│   ├── database.py         # all PyMongo code
│   ├── preprocessing.py    # load, clean, validate, split
│   ├── training.py         # train both models
│   ├── evaluation.py       # Accuracy, Precision, Recall, F1, R2, MAE
│   └── prediction.py       # forecasts and tips
├── data/
│   ├── students.csv        # sample dataset (300 students)
│   └── generate_sample_data.py
└── docs/                   # report, presentation, viva questions
```

## Step 1: Create a virtual environment

You need Python 3.9 or newer. Open a terminal inside the project folder.

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt or PowerShell)**
```bash
python -m venv venv
venv\Scripts\activate
```
(If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, then activate again.)

## Step 2: Install the libraries

```bash
pip install -r requirements.txt
```

## Step 3: Set up MongoDB (choose ONE option)

### Option A: MongoDB on your own computer
1. Download **MongoDB Community Server** from https://www.mongodb.com/try/download/community and install it (on Windows keep "Install MongoDB as a Service" ticked).
2. Make sure it is running:
   - Windows: it starts automatically as a service.
   - macOS (Homebrew): `brew services start mongodb-community`
   - Linux: `sudo systemctl start mongod`
3. Your address is `mongodb://localhost:27017` (already the default in `.env.example`).

### Option B: MongoDB Atlas (free cloud database)
1. Create a free account at https://www.mongodb.com/atlas and create a free cluster.
2. **Database Access** → add a database user (remember the username and password).
3. **Network Access** → add your current IP address (or `0.0.0.0/0` for a quick college demo only).
4. **Connect → Drivers** → copy the connection string. It looks like `mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/`.
5. Replace `<username>` and `<password>` with your own. If your password has special characters such as `@` or `#`, URL-encode them (for example `@` becomes `%40`).

## Step 4: Create your `.env` file

**macOS / Linux**
```bash
cp .env.example .env
```
**Windows**
```bash
copy .env.example .env
```
Open `.env` in any text editor. For a local MongoDB nothing needs to change. For Atlas, replace the `MONGODB_URI` line with your Atlas connection string. Also change `SECRET_KEY` to any long random text, and set `TEACHER_CODE` to your own secret (teachers type it on the Sign up page to create a teacher account). Never share or upload `.env`.

## Step 5: Load the sample data

```bash
python seed_db.py
```
This adds a demo teacher, a demo class of 6 students with some forecast history, and 300 sample exam records that belong to the **demo teacher** (so a brand-new teacher starts with an empty Exam records tab). You can run it as many times as you like; existing data is skipped, so there are no duplicates.

## Step 6: Train the forecasts

```bash
python train_models.py
```
This trains both models, prints all six metrics, saves them in MongoDB and writes `docs/results_summary.md`. Use these real numbers in your report and slides.

## Step 7: Start the website

```bash
python app.py
```
Open **http://localhost:5000** in your browser. Stop the server with `Ctrl + C`.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Teacher (class code **DEMO42**) | teacher@school.com | teacher123 |
| Student (already in the demo class) | student@school.com | student123 |

The demo class also has ananya@, rohan@, meera@, arjun@ and sneha@school.com (all with password `student123`).

### How teachers and students are connected

1. **A teacher signs up** on the Sign up page: choose *I'm a teacher* and enter the `TEACHER_CODE` from your `.env`. Without that secret code nobody can create a teacher account.
2. The teacher gets a unique **class code** (for example `K7M4QX`), shown at the top of the *My class* tab. They share it with their students.
3. **A student joins** by typing the class code when signing up, or later in the blue box on their dashboard. The student sees on screen that their teacher can see their forecasts.
4. The teacher's *My class* tab shows **only the students who joined that teacher's code**. One teacher can never open another teacher's students.
5. The *Exam records* tab shows **only the records that teacher added**. Two teachers can both use the ID `S001` without clashing, and no teacher can see, edit or delete another teacher's records.
6. The *Forecast quality* tab shows how accurate the **shared** forecasts are overall. The forecasts learn from every teacher's records, but only as numbers: no teacher can see another teacher's rows.

To try it: sign up as a teacher, copy the class code, open a private window, sign up as a student with that code, check a forecast, then look at the teacher panel.

## What is saved in MongoDB?

Database `student_performance_db`:

| Collection | Contains |
|---|---|
| `users` | accounts (email is unique, passwords are hashed, never plain text). Teachers have a `class_code`; students who joined a class have a `teacher_id` |
| `students` | exam records. Each record has the `teacher_id` of the teacher who owns it; `student_id` is unique per teacher |
| `predictions` | each user's forecast history |
| `model_evaluations` | metrics and model information of each training run |

You can look at them with the free **MongoDB Compass** app (connect with your `MONGODB_URI`).

## How the metrics are calculated

| Model | Metrics | Calculated on |
|---|---|---|
| Logistic Regression | Accuracy, Precision, Recall, F1 (positive class = Pass) | Pass/Fail labels of the test set |
| Linear Regression | R² Score, MAE | actual vs predicted marks of the test set |

Scores depend on the dataset and the train/test split (80% train, 20% test, `random_state=42`). They are shown to teachers on the **Forecast quality** tab.

## How the backend and frontend talk

The browser pages (frontend) call the Flask server (backend) with `fetch`. Main routes:

| Route | Who | What it does |
|---|---|---|
| `POST /api/register`, `/api/login`, `/api/logout` | everyone | accounts |
| `POST /api/predict` | logged-in users | forecast + tips, saved to history |
| `GET /api/predictions` | logged-in users | your own history |
| `GET /api/admin/class`, `GET /api/admin/class/<id>/history` | teachers | their own students and a student's history |
| `GET /api/my-class`, `POST /api/join-class` | students | see or change the class they joined |
| `GET /api/admin/summary` | teachers | statistics and chart data of the exam records |
| `GET/POST/PUT/DELETE /api/admin/students` | teachers | manage the exam records |
| `GET /api/admin/model`, `POST /api/admin/retrain` | teachers | forecast quality, retrain |

## Troubleshooting

| Problem | Fix |
|---|---|
| `MONGODB_URI is missing` | You did not create `.env`. Run Step 4. |
| `Could not connect to MongoDB` (local) | MongoDB is not running. Start it (Step 3, Option A). |
| `Could not connect to MongoDB` (Atlas) | Check username/password, and add your IP in Atlas → Network Access. |
| `bad auth` / `Authentication failed` | Wrong Atlas username or password in `.env`. |
| `ModuleNotFoundError: No module named ...` | Activate the virtual environment, then run `pip install -r requirements.txt`. |
| `python` not found on macOS/Linux | Use `python3` instead of `python`. |
| Website says "We can't reach our servers" | MongoDB stopped or is unreachable. Check the terminal for details, then start MongoDB. |
| "Predictions are not available yet" | Run `python train_models.py`. |
| Demo login says "Wrong email or password" | Run `python seed_db.py` first. |
| "Teacher sign-up is not available" / "access code is not correct" | Set `TEACHER_CODE` in `.env`, restart `python app.py`, and type exactly that code. |
| "We couldn't find that class code" | Check the code with the teacher (it is 6 letters/numbers, shown in the My class tab). |
| Teacher panel shows no students | Students only appear after they join with your class code. For the demo, log in as teacher@school.com (code DEMO42). |
| Port 5000 already in use (common on macOS) | Run `PORT=5001 python app.py` (Windows PowerShell: `$env:PORT=5001; python app.py`) and open http://localhost:5001. |
| Atlas connection fails on college Wi-Fi | The network may block port 27017. Try a mobile hotspot or use local MongoDB. |
| Charts do not appear | Hard-refresh the page (Ctrl + F5). The chart library is included in `static/js`. |

## Notes

- If you already ran an older version of `seed_db.py`, just run `python seed_db.py` again: it gives the demo teacher a class code, links the demo students to the demo teacher, and gives the existing 300 sample records to the demo teacher so other teachers no longer see them.
- `train_models.py` trains from `data/students.csv`, so results are reproducible. The teacher's **Update forecasts** button retrains from the exam records in MongoDB, so the numbers will change if records are added or edited.
- The built-in Flask server is for demonstration. Public deployment would need a production server, HTTPS, and extra security (email verification, password reset, rate limiting).
