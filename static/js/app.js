document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((flash) => {
    window.setTimeout(() => {
      if (flash.isConnected) {
        flash.style.transition = "opacity .35s";
        flash.style.opacity = "0";
        window.setTimeout(() => flash.remove(), 360);
      }
    }, 5500);
  });
  const password = document.querySelector("#password");
  const confirm = document.querySelector("#confirm_password");
  if (password && confirm) {
    confirm.addEventListener("input", () => {
      confirm.setCustomValidity(confirm.value && confirm.value !== password.value ? "Passwords do not match." : "");
    });
    password.addEventListener("input", () => {
      confirm.setCustomValidity(confirm.value && confirm.value !== password.value ? "Passwords do not match." : "");
    });
  }
});
