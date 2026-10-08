(function () {
  const form = document.getElementById("regForm");
  if (!form) return;

  const tabButtons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  function showStep(step) {
    tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.step === String(step)));
    panels.forEach((p) => p.classList.toggle("active", p.dataset.panel === String(step)));
  }

  tabButtons.forEach((b) => {
    b.addEventListener("click", () => showStep(Number(b.dataset.step)));
  });

  function setError(name, msg) {
    const el = form.querySelector(`.field-error[data-for="${name}"]`);
    if (el) {
      if (msg) {
        el.textContent = "❌ " + msg;
        el.classList.remove("field-ok");
      } else {
        el.textContent = "";
      }
    }
  }
  function setOk(name, msg) {
    const el = form.querySelector(`.field-error[data-for="${name}"]`);
    if (el) {
      el.textContent = "✅ " + (msg || "Valid");
      el.classList.add("field-ok");
    }
  }
  function val(name) {
    const f = form.querySelector(`[name="${name}"]`);
    return f ? (f.value || "").trim() : "";
  }
  function validatePhone(v) {
    return /^[6-9]\d{9}$/.test(v);
  }
  function validateUid(v) {
    return /^\d{9,12}$/.test(v);
  }
  function validateLevel(v) {
    const n = Number(v);
    return Number.isInteger(n) && n > 30;
  }
  function validateField(name) {
    const f = form.querySelector(`[name="${name}"]`);
    if (!f) return true;
    const rule = f.getAttribute("data-validate");
    const v = f.value.trim();
    const player = f.getAttribute("data-player");
    if (rule === "required") {
      if (!v) {
        setError(name, "This field is required.");
        return false;
      }
      setOk(name);
      return true;
    }
    if (rule === "phone") {
      if (!validatePhone(v)) {
        setError(name, "Phone number must contain exactly 10 digits.");
        return false;
      }
      setOk(name, "Valid phone");
      return true;
    }
    if (rule === "uid") {
      if (!v) { setError(name, "This field is required."); return false; }
      if (!validateUid(v)) {
        setError(name, `Player ${player} UID is invalid. Please enter a valid Free Fire UID.`);
        return false;
      }
      setOk(name, "Valid UID");
      return true;
    }
    if (rule === "level") {
      if (!v) { setError(name, "This field is required."); return false; }
      if (!validateLevel(v)) {
        setError(name, `Player ${player} level must be more than 30. Current level: ${v || 0}.`);
        return false;
      }
      setOk(name, "Valid level");
      return true;
    }
    if (rule === "screenshot") {
      const files = f.files || [];
      if (!files.length) {
        setError(name, "Please upload your payment screenshot.");
        return false;
      }
      const ok = /\.(png|jpe?g|gif|webp)$/i.test(files[0].name || "");
      if (!ok) {
        setError(name, "Invalid image type.");
        return false;
      }
      setOk(name, "Image selected");
      return true;
    }
    return true;
  }
  const allValidatable = Array.from(form.querySelectorAll("[data-validate]"));
  allValidatable.forEach((f) => {
    f.addEventListener("input", () => validateField(f.name));
    f.addEventListener("change", () => validateField(f.name));
  });

  function validateStep1() {
    let ok = true;
    ["team_name", "captain_name", "captain_phone"].forEach((n) => { if (!validateField(n)) ok = false; });
    for (let i = 1; i <= 4; i++) {
      [`player_${i}_name`, `player_${i}_uid`, `player_${i}_level`].forEach((n) => {
        if (!validateField(n)) ok = false;
      });
    }
    return ok;
  }
  function validateStep3() {
    let ok = true;
    ["payment_screenshot", "payment_transaction_id"].forEach((n) => {
      if (!validateField(n)) ok = false;
    });
    return ok;
  }

  form.addEventListener("submit", (e) => {
    if (!(validateStep1() && validateStep3())) {
      e.preventDefault();
      const s = document.getElementById("formSummaryErrors");
      if (s) { s.textContent = "Please fix the errors above before submitting."; s.classList.remove("hidden"); }
    }
  });

  const go2 = document.getElementById("goStep2");
  if (go2) go2.addEventListener("click", () => { if (validateStep1()) showStep(2); });
  const go3 = document.getElementById("goStep3");
  if (go3) go3.addEventListener("click", () => { showStep(3); });
  form.querySelectorAll("[data-back]").forEach((b) => b.addEventListener("click", () => showStep(Number(b.dataset.back))));

  // Copy UPI ID button
  const copyBtn = document.getElementById("copyUpiBtn");
  const upiEl = document.getElementById("upiIdValue");
  if (copyBtn && upiEl) {
    copyBtn.addEventListener("click", async () => {
      const text = (upiEl.textContent || "").trim();
      try {
        await navigator.clipboard.writeText(text);
        const prev = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        copyBtn.classList.add("btn-green");
        setTimeout(() => {
          copyBtn.textContent = prev;
          copyBtn.classList.remove("btn-green");
        }, 1600);
      } catch (err) {
        // Fallback for older browsers
        const range = document.createRange();
        range.selectNodeContents(upiEl);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        copyBtn.textContent = "Select & copy";
      }
    });
  }
})();
