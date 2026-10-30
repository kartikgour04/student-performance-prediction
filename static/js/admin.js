// Teacher panel: my class, exam records, forecast quality.
const PASS_MARK = 40;
const PAGE_SIZE = 10;
let students = [];
let page = 0;
let editingId = null; // null = adding a new record
const charts = {};
const LEVEL_TEXT = { great: "On track", ok: "Likely to pass", risk: "Needs support" };

// ---------------------------------------------------------------- tabs
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + tab.dataset.tab));
    if (tab.dataset.tab === "class") loadClass();
    if (tab.dataset.tab === "records") loadOverview();
    if (tab.dataset.tab === "quality") loadQuality();
  });
});

function drawChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), config);
}

// ---------------------------------------------------------------- my class
async function loadClass() {
  let c;
  try { c = await api("/api/admin/class"); } catch (e) { toast(e.message); return; }
  document.getElementById("class-code").textContent = c.class_code;

  const avg = c.average_forecast == null ? "-" : c.average_forecast + " / 100";
  const items = [["Students in class", c.total], ["Have checked a forecast", c.checked],
                 ["Need support", c.need_support], ["Average forecast", avg]];
  document.getElementById("class-stats").innerHTML = items.map(([l, v]) =>
    `<div class="card stat"><div class="label">${esc(l)}</div><div class="value">${esc(v)}</div></div>`).join("");

  document.getElementById("class-empty").style.display = c.students.length ? "none" : "block";
  document.getElementById("class-body").innerHTML = c.students.map((s) => {
    const l = s.latest;
    const cells = l
      ? `<td><b>${esc(l.predicted_marks)}</b> / 100</td>
         <td><span class="pill ${esc(l.level)}">${esc(l.pass_chance)}% &middot; ${esc(LEVEL_TEXT[l.level])}</span></td>
         <td>${esc(l.study_hours)} h</td><td>${esc(l.attendance)}%</td><td>${esc(l.previous_marks)}</td>`
      : `<td class="muted" colspan="5">Has not checked a forecast yet</td>`;
    return `<tr>
      <td class="name-cell"><b>${esc(s.name)}</b><span>${esc(s.email)}</span></td>
      ${cells}<td>${esc(s.checks)}</td>
      <td class="actions"><button class="btn ghost small" data-history="${esc(s.id)}" data-name="${esc(s.name)}">History</button></td></tr>`;
  }).join("");
}

document.getElementById("copy-code").addEventListener("click", async () => {
  const code = document.getElementById("class-code").textContent;
  try { await navigator.clipboard.writeText(code); toast("Class code copied."); }
  catch (e) { toast("Your class code is " + code); }
});

const historyDialog = document.getElementById("history-dialog");
document.getElementById("history-close").addEventListener("click", () => historyDialog.close());
document.getElementById("class-body").addEventListener("click", async (event) => {
  const id = event.target.dataset.history;
  if (!id) return;
  try {
    const r = await api("/api/admin/class/" + encodeURIComponent(id) + "/history");
    document.getElementById("history-title").textContent = r.name + " - recent checks";
    document.getElementById("history-none").style.display = r.history.length ? "none" : "block";
    document.getElementById("history-rows").innerHTML = r.history.map((h) => `
      <tr><td>${esc(formatDate(h.created_at))}</td><td>${esc(h.study_hours)} h</td><td>${esc(h.attendance)}%</td>
      <td>${esc(h.previous_marks)}</td><td><b>${esc(h.predicted_marks)}</b></td><td>${esc(Math.round(h.pass_probability * 100))}%</td></tr>`).join("");
    historyDialog.showModal();
  } catch (e) { toast(e.message); }
});

// ---------------------------------------------------------------- exam records: overview
async function loadOverview() {
  let s;
  try { s = await api("/api/admin/summary"); } catch (e) { toast(e.message); return; }
  const stats = document.getElementById("stats");
  if (!s.total) {
    stats.innerHTML = `<div class="card" style="grid-column:1/-1"><div class="empty">You have not added any exam records yet. Use "+ Add record" below to add past results for your students.</div></div>`;
    return;
  }
  const items = [
    ["Records", s.total], ["Average marks", s.average_marks + " / 100"],
    ["Pass rate", s.pass_rate + "%"], ["Avg. attendance", s.average_attendance + "%"],
  ];
  stats.innerHTML = items.map(([l, v]) => `<div class="card stat"><div class="label">${esc(l)}</div><div class="value">${esc(v)}</div></div>`).join("");

  const primary = cssVar("--primary"), green = cssVar("--green"), red = cssVar("--red"), line = cssVar("--line"), muted = cssVar("--muted");
  drawChart("chart-dist", {
    type: "bar",
    data: { labels: ["0-19", "20-39", "40-59", "60-79", "80-100"],
      datasets: [{ data: s.distribution, backgroundColor: [red, red, primary, primary, green], borderRadius: 8 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, grid: { color: line }, ticks: { color: muted, precision: 0 }, title: { display: true, text: "Records", color: muted } },
                x: { grid: { display: false }, ticks: { color: muted }, title: { display: true, text: "Exam marks", color: muted } } } },
  });
  drawChart("chart-scatter", {
    type: "scatter",
    data: { datasets: [
      { label: "Passed", data: s.scatter_pass, backgroundColor: green + "99", pointRadius: 4 },
      { label: "Failed", data: s.scatter_fail, backgroundColor: red + "cc", pointRadius: 4 } ] },
    options: { maintainAspectRatio: false, plugins: { legend: { labels: { color: muted } } },
      scales: { x: { title: { display: true, text: "Study hours per day", color: muted }, grid: { color: line }, ticks: { color: muted } },
                y: { title: { display: true, text: "Exam marks", color: muted }, grid: { color: line }, ticks: { color: muted }, min: 0, max: 100 } } },
  });
}

// ---------------------------------------------------------------- exam records: table + add/edit/delete
async function loadStudents() {
  try { students = await api("/api/admin/students"); } catch (e) { toast(e.message); return; }
  renderStudents();
}

function renderStudents() {
  const term = document.getElementById("search").value.trim().toLowerCase();
  const list = students.filter((s) => s.student_id.toLowerCase().includes(term));
  const pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
  page = Math.min(page, pages - 1);
  const visible = list.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  document.getElementById("students-empty").style.display = list.length ? "none" : "block";
  document.getElementById("students-body").innerHTML = visible.map((s) => {
    const passed = s.exam_marks >= PASS_MARK;
    return `<tr>
      <td><b>${esc(s.student_id)}</b></td><td>${esc(s.study_hours)}</td><td>${esc(s.attendance)}%</td>
      <td>${esc(s.previous_marks)}</td><td>${esc(s.exam_marks)}</td>
      <td><span class="pill ${passed ? "great" : "risk"}">${passed ? "Pass" : "Fail"}</span></td>
      <td class="actions">
        <button class="btn ghost small" data-edit="${esc(s.student_id)}">Edit</button>
        <button class="btn danger small" data-delete="${esc(s.student_id)}">Delete</button>
      </td></tr>`;
  }).join("");
  document.getElementById("page-info").textContent = list.length
    ? `${page * PAGE_SIZE + 1}-${page * PAGE_SIZE + visible.length} of ${list.length} records` : "";
  document.getElementById("prev").disabled = page === 0;
  document.getElementById("next").disabled = page >= pages - 1;
}

document.getElementById("search").addEventListener("input", () => { page = 0; renderStudents(); });
document.getElementById("prev").addEventListener("click", () => { page--; renderStudents(); });
document.getElementById("next").addEventListener("click", () => { page++; renderStudents(); });

const dialog = document.getElementById("student-dialog");
const studentForm = document.getElementById("student-form");
const dialogAlert = document.getElementById("dialog-alert");

function openDialog(student) {
  editingId = student ? student.student_id : null;
  document.getElementById("dialog-title").textContent = student ? "Edit " + student.student_id : "Add record";
  hideAlert(dialogAlert);
  studentForm.reset();
  const idField = document.getElementById("f_student_id");
  idField.disabled = !!student; // the ID cannot be changed after creation
  if (student) {
    idField.value = student.student_id;
    ["study_hours", "attendance", "previous_marks", "exam_marks"].forEach((k) => (studentForm[k].value = student[k]));
  }
  dialog.showModal();
}

document.getElementById("add-btn").addEventListener("click", () => openDialog(null));
document.getElementById("cancel-btn").addEventListener("click", () => dialog.close());

document.getElementById("students-body").addEventListener("click", async (event) => {
  const editId = event.target.dataset.edit;
  const deleteId = event.target.dataset.delete;
  if (editId) openDialog(students.find((s) => s.student_id === editId));
  if (deleteId && confirm(`Delete record ${deleteId}? This cannot be undone.`)) {
    try {
      const r = await api("/api/admin/students/" + encodeURIComponent(deleteId), "DELETE");
      toast(r.message);
      loadStudents();
      loadOverview();
    } catch (e) { toast(e.message); }
  }
});

studentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideAlert(dialogAlert);
  const body = Object.fromEntries(new FormData(studentForm));
  try {
    const r = editingId
      ? await api("/api/admin/students/" + encodeURIComponent(editingId), "PUT", body)
      : await api("/api/admin/students", "POST", body);
    dialog.close();
    toast(r.message);
    loadStudents();
    loadOverview();
  } catch (e) { showAlert(dialogAlert, e.message); }
});

// ---------------------------------------------------------------- forecast quality
const pct = (v) => (v * 100).toFixed(1) + "%";

async function loadQuality() {
  const box = document.getElementById("quality");
  let m;
  try { m = await api("/api/admin/model"); } catch (e) { box.innerHTML = `<div class="card empty">${esc(e.message)}</div>`; return; }
  if (!m.trained) {
    box.innerHTML = `<div class="card"><div class="empty">Forecasts have not been set up yet. Run <b>python train_models.py</b> once.</div></div>`;
    return;
  }
  const c = m.logistic_regression, r = m.linear_regression, cm = c.confusion_matrix;
  const metric = (name, value, about) => `<div class="metric"><div class="name">${esc(name)}</div><div class="num">${esc(value)}</div><div class="about">${esc(about)}</div></div>`;

  box.innerHTML = `
    <div class="card">
      <div class="page-head" style="margin-bottom:0">
        <div><h2>Pass / Fail forecast</h2>
          <p class="muted" style="margin:0">Checked on ${esc(m.test_rows)} students the system had never seen.</p></div>
        <button class="btn" id="retrain-btn">Update forecasts with latest records</button>
      </div>
      <div id="quality-alert" class="alert" role="alert"></div>
      <div class="metric-grid">
        ${metric("Accuracy", pct(c.accuracy), "Share of all predictions that were right")}
        ${metric("Precision", pct(c.precision), "When we say Pass, how often it is right")}
        ${metric("Recall", pct(c.recall), "Share of real passes we caught")}
        ${metric("F1 Score", pct(c.f1_score), "Balance of precision and recall")}
      </div>
      <p class="muted" style="font-size:.88rem">Of the test students: ${esc(cm.true_positive)} correctly forecast to pass, ${esc(cm.true_negative)} correctly forecast to fail, ${esc(cm.false_positive)} wrongly forecast to pass, ${esc(cm.false_negative)} wrongly forecast to fail.</p>
    </div>
    <div class="two-col" style="margin-top:24px">
      <div class="card">
        <h2>Marks forecast</h2>
        <div class="metric-grid two">
          ${metric("R² Score", r.r2_score.toFixed(3), "How much of the difference in marks is explained (1 = perfect)")}
          ${metric("MAE", r.mae.toFixed(1) + " marks", "Average gap between forecast and real marks")}
        </div>
        <p class="muted" style="font-size:.88rem">What the forecast learned (extra marks for +1):<br>
          study hour: <b>${r.coefficients.study_hours.toFixed(2)}</b> &middot; attendance point: <b>${r.coefficients.attendance.toFixed(2)}</b> &middot; last-exam mark: <b>${r.coefficients.previous_marks.toFixed(2)}</b></p>
      </div>
      <div class="card">
        <h2>Forecast vs real marks</h2>
        <div class="chart-box"><canvas id="chart-actual"></canvas></div>
      </div>
    </div>
    <p class="disclaimer">These numbers describe how accurate the shared forecasts are overall. They are not about your own students. Scores depend on the data used and how it was split into practice and test groups. Data source: ${esc(m.dataset)}. Training rows: ${esc(m.train_rows)}, test rows: ${esc(m.test_rows)}.</p>`;

  const primary = cssVar("--primary"), line = cssVar("--line"), muted = cssVar("--muted");
  const points = m.test_results.actual_marks.map((a, i) => ({ x: a, y: m.test_results.predicted_marks[i] }));
  drawChart("chart-actual", {
    type: "scatter",
    data: { datasets: [
      { label: "Students", data: points, backgroundColor: primary + "aa", pointRadius: 4 },
      { label: "Perfect forecast", type: "line", data: [{ x: 0, y: 0 }, { x: 100, y: 100 }], borderColor: muted, borderDash: [6, 6], pointRadius: 0 } ] },
    options: { maintainAspectRatio: false, plugins: { legend: { labels: { color: muted } } },
      scales: { x: { min: 0, max: 100, title: { display: true, text: "Real marks", color: muted }, grid: { color: line }, ticks: { color: muted } },
                y: { min: 0, max: 100, title: { display: true, text: "Forecast marks", color: muted }, grid: { color: line }, ticks: { color: muted } } } },
  });

  document.getElementById("retrain-btn").addEventListener("click", async (event) => {
    const btn = event.target, alertBox = document.getElementById("quality-alert");
    hideAlert(alertBox);
    btn.disabled = true; btn.textContent = "Updating...";
    try {
      const res = await api("/api/admin/retrain", "POST");
      toast(res.message);
      loadQuality();
    } catch (e) {
      showAlert(alertBox, e.message);
      btn.disabled = false; btn.textContent = "Update forecasts with latest records";
    }
  });
}

loadClass();
loadStudents();
