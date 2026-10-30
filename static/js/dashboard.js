// Student dashboard: sliders, forecast, history.
const form = document.getElementById("predict-form");
const alertBox = document.getElementById("alert");
const button = document.getElementById("predict-btn");
let historyChart = null;

// Show the slider value next to its label
["study_hours", "attendance", "previous_marks"].forEach((id) => {
  const input = document.getElementById(id);
  const output = document.getElementById("o_" + id);
  const update = () => (output.textContent = input.value);
  input.addEventListener("input", update);
  update();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideAlert(alertBox);
  button.disabled = true;
  button.textContent = "Checking...";
  try {
    const result = await api("/api/predict", "POST", {
      study_hours: form.study_hours.value,
      attendance: form.attendance.value,
      previous_marks: form.previous_marks.value,
    });
    showResult(result);
    loadHistory();
  } catch (error) {
    showAlert(alertBox, error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Check my forecast";
  }
});

function showResult(r) {
  const pct = Math.round(r.pass_probability * 100);
  const pillText = { great: "On track", ok: "Likely to pass", risk: "Needs attention" }[r.level];
  document.getElementById("result").innerHTML = `
    <div class="result-top">
      <div class="ring ${r.level === "great" ? "" : r.level}" style="--p:${pct}"><span>${pct}%</span></div>
      <div>
        <div class="muted">Expected marks</div>
        <div class="marks">${esc(r.predicted_marks)} <small>/ 100</small></div>
        <div style="margin-top:8px"><span class="pill ${esc(r.level)}">${esc(pillText)}</span></div>
      </div>
    </div>
    <p style="margin:18px 0 0"><b>${esc(r.headline)}</b><br>
      <span class="muted">${pct}% chance of passing (pass mark is ${esc(r.pass_mark)}).</span></p>
    <ul class="tips">${r.tips.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
}

async function loadHistory() {
  let rows = [];
  try { rows = await api("/api/predictions"); } catch (e) { return; }

  const body = document.getElementById("history-body");
  document.getElementById("history-empty").style.display = rows.length ? "none" : "block";
  body.innerHTML = rows.slice(0, 8).map((r) => `
    <tr>
      <td>${esc(formatDate(r.created_at))}</td>
      <td>${esc(r.study_hours)} h</td>
      <td>${esc(r.attendance)}%</td>
      <td>${esc(r.previous_marks)}</td>
      <td><b>${esc(r.predicted_marks)}</b></td>
    </tr>`).join("");

  const chartBox = document.querySelector(".chart-box");
  const enough = rows.length >= 2;
  chartBox.style.display = enough ? "block" : "none";
  document.getElementById("chart-empty").style.display = enough ? "none" : "block";
  if (!enough) return;

  const ordered = rows.slice().reverse(); // oldest first
  const labels = ordered.map((r, i) => "#" + (i + 1));
  const primary = cssVar("--primary"), line = cssVar("--line"), muted = cssVar("--muted");
  if (historyChart) historyChart.destroy();
  historyChart = new Chart(document.getElementById("history-chart"), {
    type: "line",
    data: { labels, datasets: [{
      label: "Expected marks", data: ordered.map((r) => r.predicted_marks),
      borderColor: primary, backgroundColor: primary + "22", fill: true, tension: .3, pointRadius: 4,
    }] },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 100, grid: { color: line }, ticks: { color: muted } },
        x: { grid: { display: false }, ticks: { color: muted }, title: { display: true, text: "Your checks, oldest to newest", color: muted } },
      },
    },
  });
}

// ---------------------------------------------------------------- class (teacher link)
async function loadClass() {
  const box = document.getElementById("class-banner");
  let info;
  try { info = await api("/api/my-class"); } catch (e) { return; }
  box.style.display = "flex";
  if (info.joined) {
    box.className = "card banner joined";
    box.innerHTML = `<div><b>You are in ${esc(info.teacher_name)}'s class.</b><br>
      <span class="muted">Your teacher can see your forecasts so they can support you.</span></div>
      <button class="btn ghost small" id="change-class">Change class</button>`;
    document.getElementById("change-class").addEventListener("click", () => showJoinForm(box, true));
  } else {
    showJoinForm(box, false);
  }
}

function showJoinForm(box, changing) {
  box.className = "card banner";
  box.innerHTML = `<div><b>${changing ? "Join a different class" : "Join your teacher's class"}</b><br>
    <span class="muted">Enter the class code your teacher gave you. They will be able to see your forecasts.</span></div>
    <form id="join-form"><input type="text" id="join-code" maxlength="12" placeholder="Class code" aria-label="Class code" required>
    <button class="btn" type="submit">Join</button></form>`;
  document.getElementById("join-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const r = await api("/api/join-class", "POST", { class_code: document.getElementById("join-code").value });
      toast("You joined " + r.teacher_name + "'s class.");
      loadClass();
    } catch (e) { toast(e.message); }
  });
}

loadClass();
loadHistory();
