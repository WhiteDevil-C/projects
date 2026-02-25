/**
 * Professional Face Recognition Camera Pipeline
 */

const elements = {
  video: document.getElementById("cam"),
  canvas: document.getElementById("overlay"),
  status: document.getElementById("status"),
  camStatusDot: document.getElementById("camStatusDot"),
  camStatusText: document.getElementById("camStatusText"),
  videoSource: document.getElementById("videoSource"),
  btnToggleCam: document.getElementById("btnToggleCam"),
  perfCounter: document.getElementById("perfCounter"),
  scanLine: document.getElementById("scanLine"),

  // Existing Dashboard Elements
  metricUsers: document.getElementById("metricUsers"),
  metricAwards: document.getElementById("metricAwards"),
  metricModel: document.getElementById("metricModel"),
  toastContainer: document.getElementById("toastContainer"),
  regName: document.getElementById("regName"),
  regEmail: document.getElementById("regEmail"),
  verifyResult: document.getElementById("verifyResult"),
  awardName: document.getElementById("awardName"),
  awardTitle: document.getElementById("awardTitle"),
  awardResult: document.getElementById("awardResult")
};

// State
let stream = null;
let isCamActive = false;
let isRequestPending = false;
let abortController = null;
let scanInterval = null;
let activeMode = null; // 'register' or 'verify'

/**
 * Toast / Status Helpers
 */
function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast-msg fade-in`;
  const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
  el.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  elements.toastContainer.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 3000);
}

function updateStatus(msg, active = false) {
  if (!elements.status) return;
  elements.status.textContent = msg;
  if (elements.camStatusDot) elements.camStatusDot.className = active ? "status-dot active" : "status-dot";
  if (elements.camStatusText) elements.camStatusText.textContent = active ? "Live: Scanning" : "Camera Offline";
  if (elements.scanLine) elements.scanLine.style.display = active ? "block" : "none";
}

/**
 * Camera Device Management
 */
async function getDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    if (!elements.videoSource) return;
    elements.videoSource.innerHTML = "";
    devices.filter(d => d.kind === "videoinput").forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.deviceId;
      opt.text = d.label || `Camera ${elements.videoSource.length + 1}`;
      elements.videoSource.appendChild(opt);
    });
  } catch (err) {
    console.error("Error listing devices:", err);
  }
}

async function startCamera() {
  const deviceId = elements.videoSource?.value;
  const constraints = {
    video: {
      deviceId: deviceId ? { exact: deviceId } : undefined,
      width: { ideal: 1280 },
      height: { ideal: 720 }
    }
  };

  try {
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    elements.video.srcObject = stream;
    isCamActive = true;
    if (elements.btnToggleCam) elements.btnToggleCam.querySelector(".btn-text").textContent = "Stop Camera";
    updateStatus("Camera Active", true);

    // Sync canvas size to video actual size
    elements.video.onloadedmetadata = () => {
      elements.canvas.width = elements.video.videoWidth;
      elements.canvas.height = elements.video.videoHeight;
    };

    startPipeline();
  } catch (err) {
    showToast("Error starting camera: " + err.message, "error");
    updateStatus("Failed to start camera");
  }
}

function stopCamera() {
  isCamActive = false;
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  if (elements.video) elements.video.srcObject = null;
  if (elements.btnToggleCam) elements.btnToggleCam.querySelector(".btn-text").textContent = "Start Camera";
  updateStatus("Camera Offline", false);

  if (abortController) abortController.abort();
  if (scanInterval) clearInterval(scanInterval);

  // Clear canvas
  const ctx = elements.canvas.getContext("2d");
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
}

window.toggleCamera = () => {
  if (isCamActive) stopCamera();
  else startCamera();
};

/**
 * Scanning Pipeline
 */
function startPipeline() {
  if (scanInterval) clearInterval(scanInterval);
  scanInterval = setInterval(async () => {
    if (!isCamActive || isRequestPending || !activeMode) return;
    if (document.visibilityState !== "visible") return;

    await captureAndProcess();
  }, 500); // 500ms throttling
}

async function captureAndProcess() {
  isRequestPending = true;
  abortController = new AbortController();

  // Capture Frame
  const captureCanvas = document.createElement("canvas");
  captureCanvas.width = elements.video.videoWidth;
  captureCanvas.height = elements.video.videoHeight;
  captureCanvas.getContext("2d").drawImage(elements.video, 0, 0);
  const base64 = captureCanvas.toDataURL("image/jpeg", 0.7);

  try {
    const response = await fetch("/process_frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: base64 }),
      signal: abortController.signal
    });

    const data = await response.json();
    if (data.ok) {
      drawOverlays(data.faces);
      if (elements.perfCounter) elements.perfCounter.textContent = `${data.processing_ms}ms`;

      if (activeMode === "verify" && data.matched) {
        handleMatch(data.name);
      }

      if (activeMode === "register") {
        handleRegisterFrame(base64);
      }
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      updateStatus("Processing error: " + err.message);
    }
  } finally {
    isRequestPending = false;
  }
}

function drawOverlays(faces) {
  const ctx = elements.canvas.getContext("2d");
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);

  faces.forEach(f => {
    const color = f.matched ? "#10b981" : "#ef4444";
    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
    ctx.strokeRect(f.x, f.y, f.w, f.h);

    // Label
    ctx.fillStyle = color;
    ctx.font = "bold 20px sans-serif";
    ctx.fillText(`${f.label} (${Math.round(f.confidence)})`, f.x, f.y - 10);
  });
}

/**
 * App Logic Handlers
 */
let registerCount = 0;
async function handleRegisterFrame(base64) {
  const name = elements.regName.value.trim();
  if (!name) return;

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email: elements.regEmail.value, image: base64 })
    });
    const data = await res.json();
    if (data.captured) {
      registerCount++;
      updateStatus(`Registration: Captured ${registerCount}/25`, true);
      if (registerCount >= 25) {
        showToast("Registration Complete!", "success");
        activeMode = null;
        registerCount = 0;
        elements.regName.value = "";
        elements.regEmail.value = "";
      }
    }
  } catch (e) { }
}

function handleMatch(name) {
  showToast(`Welcome back, ${name}!`, "success");
  if (elements.awardName) elements.awardName.value = name;
  if (elements.verifyResult) {
    elements.verifyResult.innerHTML = `<span style="color:#10b981">Verified: <b>${name}</b></span>`;
  }
}

/**
 * Public Actions
 */
window.registerUser = () => {
  if (!elements.regName.value.trim()) return showToast("Enter name for registration", "error");
  if (!isCamActive) return showToast("Start camera first", "info");
  activeMode = "register";
  registerCount = 0;
  updateStatus("Registration mode active", true);
};

window.verifyFace = () => {
  if (!isCamActive) return showToast("Start camera first", "info");
  activeMode = "verify";
  const cancelBtn = document.getElementById("btnCancelVerify");
  if (cancelBtn) cancelBtn.style.display = "inline-flex";
  updateStatus("Verification mode active", true);
};

window.cancelVerify = () => {
  activeMode = null;
  const cancelBtn = document.getElementById("btnCancelVerify");
  if (elements.verifyResult) elements.verifyResult.textContent = "Waiting for input...";
  // Clear overlay
  const ctx = elements.canvas.getContext("2d");
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
  updateStatus("Camera Active", isCamActive);
  showToast("Verification cancelled", "info");
};

window.trainModel = async () => {
  updateStatus("Training model...", true);
  try {
    const res = await fetch("/api/v1/train", { method: "POST" });
    const data = await res.json();
    showToast("Model trained successfully!", "success");
    if (elements.metricModel) elements.metricModel.textContent = "Active";
  } catch (e) { showToast("Training failed", "error"); }
  finally { updateStatus("System Ready", isCamActive); }
};

window.generateAward = async () => {
  const name = elements.awardName.value;
  const title = elements.awardTitle.value;
  if (!name) return showToast("Verify user first", "error");

  try {
    const res = await fetch("/api/award", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, award_title: title })
    });
    const data = await res.json();
    if (elements.awardResult) {
      elements.awardResult.innerHTML = `<a href="${data.download_url}" target="_blank">Download Certificate</a>`;
    }
    showToast("Award generated!", "success");
  } catch (e) { showToast("Failed to generate award", "error"); }
};

// Start Up
getDevices();
if (navigator.mediaDevices.ondevicechange !== undefined) {
  navigator.mediaDevices.ondevicechange = getDevices;
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible") {
    // Optional: throttle heavily or pause requests
  }
});

