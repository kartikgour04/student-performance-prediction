// Small helpers shared by every page.

// Call the backend. Returns the JSON, or throws an Error with a friendly message.
async function api(url, method = "GET", body = null) {
  const options = { method, headers: {} };
  if (body !== null) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(url, options);
  } catch (e) {
    throw new Error("Can't reach the server. Please check your connection.");
  }
  let data = {};
  try { data = await response.json(); } catch (e) { /* empty body */ }
  if (response.status === 401 && !url.startsWith("/api/login")) {
    window.location = "/login";
    throw new Error("Please log in.");
  }
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

// Put text safely into the page (never as HTML).
function esc(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function toast(message) {
  let el = document.getElementById("toast");
  if (!el) { el = document.createElement("div"); el.id = "toast"; el.className = "toast"; document.body.appendChild(el); }
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 2600);
}

function showAlert(el, message, type = "error") {
  el.textContent = message;
  el.className = "alert show " + type;
}
function hideAlert(el) { el.className = "alert"; }

async function logout() {
  try { const r = await api("/api/logout", "POST"); window.location = r.redirect; }
  catch (e) { window.location = "/"; }
}
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-logout]")) { e.preventDefault(); logout(); }
});

// Chart colours that read the page's CSS variables (works in light and dark mode).
function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
