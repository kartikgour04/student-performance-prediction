// Login and sign-up forms.
const form = document.getElementById("auth-form");
const alertBox = document.getElementById("alert");
const button = form.querySelector("button[type=submit]");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideAlert(alertBox);
  const body = Object.fromEntries(new FormData(form));
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Please wait...";
  try {
    const result = await api(form.dataset.endpoint, "POST", body);
    window.location = result.redirect;
  } catch (error) {
    showAlert(alertBox, error.message);
    button.disabled = false;
    button.textContent = label;
  }
});
