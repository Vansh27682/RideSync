document.addEventListener("DOMContentLoaded", () => {
  const modal = document.querySelector("#booking-modal");
  if (!modal) return;
  const form = document.querySelector("#booking-form");
  const name = document.querySelector("#modal-vehicle-name");
  const rateLabel = document.querySelector("#modal-vehicle-rate");
  const duration = document.querySelector("#duration");
  const total = document.querySelector("#estimated-total");
  const start = document.querySelector("#start_time");
  let hourlyRate = 0;
  const minDate = new Date(Date.now() + 5 * 60 * 1000);
  const localValue = new Date(minDate.getTime() - minDate.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  start.min = localValue;
  function updateTotal() {
    total.textContent = "₹" + (hourlyRate * Number(duration.value || 1)).toLocaleString("en-IN");
  }
  document.querySelectorAll(".book-trigger").forEach(button => {
    button.addEventListener("click", () => {
      hourlyRate = Number(button.dataset.vehiclePrice);
      name.textContent = button.dataset.vehicleName;
      rateLabel.textContent = "₹" + hourlyRate + " / hour";
      form.action = "/book/" + button.dataset.vehicleId;
      duration.value = "1";
      updateTotal();
      modal.classList.add("open");
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      start.focus();
    });
  });
  duration.addEventListener("change", updateTotal);
  function closeModal() {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
  document.querySelector("#modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", event => { if (event.target === modal) closeModal(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeModal(); });
  form.addEventListener("submit", event => {
    if (!start.value || new Date(start.value) <= new Date()) {
      event.preventDefault();
      start.setCustomValidity("Please select a future pickup time.");
      start.reportValidity();
      start.addEventListener("input", () => start.setCustomValidity(""), {once:true});
    }
  });
});
