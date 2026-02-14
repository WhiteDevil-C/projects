const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const statusPing = document.getElementById("statusPing");
const toastContainer = document.getElementById("toastContainer");

// Status Helpers
function setSystemStatus(msg, type = "ready") {
  statusText.textContent = msg;
  let color = "#10b981"; // success
  if (type === "busy") color = "#f59e0b"; // warning
  if (type === "error") color = "#ef4444"; // error

  statusDot.style.background = color;
  statusPing.style.background = color;

  if (type === "busy") {
    statusPing.style.animationDuration = "0.8s";
  } else {
    statusPing.style.animationDuration = "1.5s";
  }
}

function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = "toast-msg";

  let icon = "ℹ️";
  if (type === "success") icon = "✅";
  if (type === "error") icon = "❌";
  if (type === "loading") icon = "⏳";

  el.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;

  toastContainer.appendChild(el);

  // Auto remove
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(50%)";
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

// API Helper
async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

// UI Helpers
function setLoading(btnId, isLoading, originalText = "") {
  const btn = document.getElementById(btnId);
  if (!btn) return;

  const iconSpan = btn.querySelector(".btn-icon");
  const textSpan = btn.querySelector(".btn-text");

  if (isLoading) {
    btn.disabled = true;
    btn.dataset.originalText = textSpan.textContent;
    btn.dataset.originalIcon = iconSpan.textContent;

    // Add spinner
    iconSpan.textContent = "";
    iconSpan.classList.add("spinner"); // You might want to add a spinner CSS class
    textSpan.textContent = "Processing...";

    // Simple spinner replacement if CSS class isn't enough
    iconSpan.innerHTML = "⏳";
    iconSpan.style.animation = "spin 1s linear infinite";
  } else {
    btn.disabled = false;
    textSpan.textContent = btn.dataset.originalText || originalText;
    iconSpan.textContent = btn.dataset.originalIcon || "";
    iconSpan.style.animation = "none";
  }
}

// Modal
function openHelp() { document.getElementById("helpModal").classList.add("show"); }
function closeHelp() { document.getElementById("helpModal").classList.remove("show"); }
window.openHelp = openHelp;
window.closeHelp = closeHelp;

// Metrics
function setMetric(id, val) {
  const el = document.getElementById(id);
  if (el) {
    el.style.transform = "scale(1.2)";
    el.textContent = val;
    setTimeout(() => el.style.transform = "scale(1)", 200);
  }
}

// Global State
let metricUsersCount = 0;
let metricAwardsCount = 0;
let modelTrained = false;

// --- Actions ---

async function registerUser() {
  const nameInput = document.getElementById("regName");
  const emailInput = document.getElementById("regEmail");
  const name = nameInput.value.trim();
  const email = emailInput.value.trim();

  if (!name) return showToast("Please enter a name first", "error");

  setLoading("btnRegister", true);
  setSystemStatus("Capturing faces...", "busy");
  const statusEl = document.getElementById("regStatus");
  statusEl.textContent = "Camera active. Look at camera...";
  statusEl.style.color = "#06b6d4";

  try {
    const data = await postJSON("/api/register", { name, email });
    metricUsersCount++;
    setMetric("metricUsers", metricUsersCount);

    showToast(`Registered ${name} successfully!`, "success");
    statusEl.textContent = "Capture complete!";
    statusEl.style.color = "#10b981";

    // Clear inputs
    nameInput.value = "";
    emailInput.value = "";

  } catch (e) {
    showToast(e.message, "error");
    statusEl.textContent = "Error: " + e.message;
    statusEl.style.color = "#ef4444";
  } finally {
    setLoading("btnRegister", false);
    setSystemStatus("System Ready", "ready");
  }
}

async function trainModel() {
  setLoading("btnTrain", true);
  setSystemStatus("Training Model...", "busy");
  const statusEl = document.getElementById("trainStatus");
  statusEl.textContent = "Training in progress...";
  statusEl.style.color = "#a855f7";

  try {
    await postJSON("/api/train", {});
    modelTrained = true;
    setMetric("metricModel", "Active");

    showToast("Model trained successfully!", "success");
    statusEl.textContent = "Model updated & ready.";
    statusEl.style.color = "#10b981";
  } catch (e) {
    showToast(e.message, "error");
    statusEl.textContent = "Training failed.";
    statusEl.style.color = "#ef4444";
  } finally {
    setLoading("btnTrain", false);
    setSystemStatus("System Ready", "ready");
  }
}

async function verifyFace() {
  setLoading("btnVerify", true);
  setSystemStatus("Verifying identity...", "busy");
  const resultBox = document.getElementById("verifyResult");
  resultBox.textContent = "Scanning...";
  resultBox.style.borderColor = "#3b82f6";

  try {
    const data = await postJSON("/api/verify", {});
    if (data.matched) {
      resultBox.innerHTML = `<span style="color:#10b981">Match Found: <b>${data.name}</b></span>`;
      resultBox.style.borderColor = "#10b981";
      resultBox.style.background = "rgba(16, 185, 129, 0.1)";

      document.getElementById("awardName").value = data.name;
      showToast(`Welcome back, ${data.name}!`, "success");
    } else {
      resultBox.innerHTML = `<span style="color:#ef4444">No match found.</span>`;
      resultBox.style.borderColor = "#ef4444";
      resultBox.style.background = "rgba(239, 68, 68, 0.1)";
      showToast("Verification failed", "error");
    }
  } catch (e) {
    showToast(e.message, "error");
    resultBox.textContent = "Error occurred";
  } finally {
    setLoading("btnVerify", false);
    setSystemStatus("System Ready", "ready");
  }
}

async function generateAward() {
  const name = document.getElementById("awardName").value.trim();
  const title = document.getElementById("awardTitle").value.trim() || "Certificate of Achievement";

  if (!name) return showToast("Please verify a user first", "error");

  setLoading("btnAward", true);
  setSystemStatus("Generating Certificate...", "busy");
  const resultBox = document.getElementById("awardResult");

  try {
    const data = await postJSON("/api/award", { name, award_title: title });
    metricAwardsCount++;
    setMetric("metricAwards", metricAwardsCount);

    resultBox.innerHTML = `Generated! <a href="${data.download_url}" target="_blank" style="color:#f59e0b; font-weight:bold; text-decoration:underline;">Download PDF</a>`;
    showToast("Certificate ready!", "success");
  } catch (e) {
    showToast(e.message, "error");
    resultBox.textContent = "Generation failed";
  } finally {
    setLoading("btnAward", false);
    setSystemStatus("System Ready", "ready");
  }
}

// Expose to window
window.registerUser = registerUser;
window.trainModel = trainModel;
window.verifyFace = verifyFace;
window.generateAward = generateAward;
