/* CortexFlow newsletter forms: AJAX subscribe with inline status, no-JS fallback intact. */
(function () {
  function onSubmit(e) {
    var form = e.target;
    if (!form.matches("[data-nl-form]")) return;
    e.preventDefault();
    var email = form.querySelector('input[name="email"]');
    var msg = form.querySelector(".nl-msg");
    var btn = form.querySelector('button[type="submit"]');
    var show = function (text, ok) {
      msg.hidden = false;
      msg.textContent = text;
      msg.classList.toggle("nl-ok", !!ok);
      msg.classList.toggle("nl-err", !ok);
    };
    var val = (email.value || "").trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(val)) {
      show("Please enter a valid email address.", false);
      email.focus();
      return;
    }
    btn.disabled = true;
    btn.textContent = "Subscribing…";
    var body = {
      email: val,
      website: form.querySelector('input[name="website"]').value || "",
      source: (form.querySelector('input[name="source"]') || {}).value || "site",
    };
    fetch("/api/subscribe", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json().catch(function () {
          return { ok: false, error: "Something went wrong. Please try again." };
        });
      })
      .then(function (data) {
        if (data.ok) {
          show("Subscribed. See you in the next dispatch.", true);
          form.reset();
        } else {
          show(data.error || "Something went wrong. Please try again.", false);
        }
      })
      .catch(function () {
        show("Network error. Please try again.", false);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = "Subscribe";
      });
  }
  document.addEventListener("submit", onSubmit);
})();
