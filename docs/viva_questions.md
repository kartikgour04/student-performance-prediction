# Viva Questions and Short Answers

## Python

**1. Why did you use Python for this project?**
It is simple to read and has ready-made libraries for databases (PyMongo), data (pandas), Machine Learning (scikit-learn) and websites (Flask).

**2. What is pandas and where did you use it?**
pandas is a library for working with tables of data. I used it to read the CSV file, check missing values, clean the data and prepare inputs for the models.

## MongoDB and PyMongo

**3. What is MongoDB? How is it different from SQL databases?**
MongoDB is a NoSQL database that stores data as documents (like Python dictionaries) in collections. SQL databases store data in tables with fixed rows and columns.

**4. What is PyMongo?**
PyMongo is the official Python library used to connect to MongoDB and run operations like insert, find, update and delete.

**5. Which database, collections and CRUD operations did you use?**
Database `student_performance_db`; collections `students`, `model_evaluations` and `predictions`. CRUD: `insert_one`, `find`, `update_one`, `delete_one`.

**6. How did you stop duplicate students?**
I created a unique index on `student_id`. MongoDB rejects a duplicate and my code catches the `DuplicateKeyError` and shows a friendly message. The seed script also uses upsert with `$setOnInsert`, so it is safe to run again.

**7. Why is the connection string kept in a `.env` file?**
It can contain a username and password. Keeping it out of the code and out of GitHub (`.gitignore`) protects it.

## Machine Learning Models

**8. What is Linear Regression and what does it predict here?**
It finds a straight-line relationship between inputs and a number. Here it predicts the expected exam marks from study hours, attendance and previous marks.

**9. What is Logistic Regression and why is it used for Pass/Fail?**
It is a classification model. It gives the probability of passing (0 to 1). If it is 0.5 or more we say Pass, otherwise Fail.

**10. How did you define Pass and Fail?**
Pass is exam marks of 40 or more. Fail is below 40.

## Preprocessing

**11. What preprocessing did you do?**
Loaded the CSV, checked missing values, removed duplicate IDs and out-of-range values, selected features, and split the data into 80% train and 20% test.

**12. What is data leakage and how did you avoid it?**
Data leakage is giving the model the answer by mistake. I never used exam marks as an input. Only study hours, attendance and previous marks are inputs, and the test data is not used for training.

**13. Why is `random_state=42` used?**
It fixes the random split so the same rows go to train and test every time. That makes results reproducible.

**14. Why did you scale data for Logistic Regression but not Linear Regression?**
Logistic Regression trains better when the inputs are on a similar scale. Scaling does not change Linear Regression's predictions, so it is not needed there.

## Metrics

**15. Explain Accuracy, Precision, Recall and F1 Score.**
Accuracy: how many predictions were correct overall. Precision: when we say Pass, how often it is right. Recall: of the students who really passed, how many we found. F1: a balance of Precision and Recall.

**16. Explain R² Score and MAE.**
R² tells how much of the variation in marks the model explains (1 is perfect). MAE is the average number of marks the prediction is wrong by (lower is better).

**17. Why are R² and MAE not used for the Pass/Fail model?**
They measure errors in numbers, so they belong to the marks (regression) model. Accuracy, Precision, Recall and F1 measure right and wrong classes, so they belong to the Pass/Fail (classification) model.

## Limitations and Future Scope

**18. Is your dataset real? What does that mean for your results?**
No, it is synthetic (computer-generated). The results show that the system works, but they may not apply to real students.

**19. What are the limitations of the project?**
Synthetic and small dataset, only three features, simple models, predictions are estimates not guarantees, and login is basic (no email verification or password reset).

**20. What is the future scope?**
Use real permitted data, add more features, try models like Random Forest, use cross-validation, add email verification and password reset, link student accounts to records, and deploy online with HTTPS.

## Website (frontend and backend)

**21. What is the frontend and what is the backend in your project?**
The frontend is what the user sees in the browser: HTML, CSS and JavaScript. The backend is the Flask program on the server. It checks logins, runs the ML models and talks to MongoDB. They communicate through a JSON API using `fetch`.

**22. How do you keep passwords and pages safe?**
Passwords are never stored as plain text; they are hashed with werkzeug. Logins use a signed session cookie. Teacher-only pages and API routes check the user's role. Limitations: no email verification or rate limiting, so it is for demonstration use.

**23. What real-life problem does your project solve?**
Students usually learn they are struggling only after the results. My system gives an early forecast of marks and pass chance with simple tips, and it shows teachers which students in their class may need support before the exam.

**24. How does a teacher know which students are theirs?**
Each teacher gets a unique 6-character class code. A student joins by entering it, and the student's account then stores that teacher's ID. The teacher panel only shows students with that teacher ID.

**25. How do you stop a student from becoming a teacher?**
Creating a teacher account needs a secret teacher access code stored in the `.env` file, and the role is checked on the server for every teacher route.

**26. Can one teacher see another teacher's exam records?**
No. Every exam record stores the ID of the teacher who owns it, and every read, edit and delete filters by the logged-in teacher's ID. Only the shared ML model learns from all records, as numbers.
