/**
 * Premium Face Recognition Camera Pipeline
 */

const elements = {
  video: document.getElementById("cam"),
  canvas: document.getElementById("overlay"),
  status: document.getElementById("status"),
  camStatusChip: document.getElementById("camStatusChip"),
  camStatusText: document.getElementById("camStatusText"),
  videoSource: document.getElementById("videoSource"),
  btnToggleCam: document.getElementById("btnToggleCam"),
  perfCounter: document.getElementById("perfCounter"),
  scanLine: document.getElementById("scanLine"),

  // Dashboard Metrics
  metricUsers: document.getElementById("metricUsers"),
  metricModel: document.getElementById("metricModel"),
  metricVerified: document.getElementById("metricVerified"),
  toastContainer: document.getElementById("toastContainer"),

  // Registration
  regName: document.getElementById("regName"),
  regEmail: document.getElementById("regEmail"),
  regStatus: document.getElementById("regStatus"),
  btnRegister: document.getElementById("btnRegister"),

  // Training
  btnTrain: document.getElementById("btnTrain"),
  trainStatus: document.getElementById("trainStatus"),

  // Verification
  verifyResult: document.getElementById("verifyResult"),
  btnVerify: document.getElementById("btnVerify"),
  btnCancelVerify: document.getElementById("btnCancelVerify")
};

// State
let stream = null;
let isCamActive = false;
let isRequestPending = false;
let abortController = null;
let scanInterval = null;
let activeMode = null; // 'register' or 'verify'
let verifiedCount = 0;

/**
 * UI Helpers
 */
function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast-msg`;
  const icon = type === "success" ? "ph-check-circle" : type === "error" ? "ph-warning-circle" : "ph-info";
  el.innerHTML = `<i class="ph ${icon}"></i> <span>${msg}</span>`;
  elements.toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(10px)";
    setTimeout(() => el.remove(), 400);
  }, 3000);
}

function updateStatus(msg, active = false) {
  if (elements.status) elements.status.textContent = msg;
  const panel = document.getElementById("camPanel");

  if (elements.camStatusChip) {
    elements.camStatusChip.className = active ? "status-chip active" : "status-chip";
  }
  if (elements.camStatusText) {
    elements.camStatusText.textContent = active ? "NEURAL_PIPELINE // ACTIVE" : "SYSTEM OFFLINE";
  }
  if (elements.scanLine) {
    elements.scanLine.style.display = active ? "block" : "none";
  }

  if (panel) {
    if (active) panel.classList.add("active");
    else panel.classList.remove("active");
  }
}

function setBtnLoading(btn, isLoading, originalText) {
  if (!btn) return;
  if (isLoading) {
    btn.disabled = true;
    btn.innerHTML = `<i class="ph ph-circle-notch ph-spin"></i> <span>SYNCING...</span>`;
  } else {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

/**
 * Camera Management
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
    if (elements.btnToggleCam) {
      elements.btnToggleCam.innerHTML = `<i class="ph ph-stop-circle"></i> <span>Stop Camera</span>`;
    }
    updateStatus("Camera Active", true);

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
  if (elements.btnToggleCam) {
    elements.btnToggleCam.innerHTML = `<i class="ph ph-video-camera"></i> <span>Start Camera</span>`;
  }
  updateStatus("Camera Offline", false);

  if (abortController) abortController.abort();
  if (scanInterval) clearInterval(scanInterval);

  const ctx = elements.canvas.getContext("2d");
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
}

window.toggleCamera = () => {
  if (isCamActive) stopCamera();
  else startCamera();
};

/**
 * Pipeline
 */
function startPipeline() {
  if (scanInterval) clearInterval(scanInterval);
  scanInterval = setInterval(async () => {
    if (!isCamActive || isRequestPending || !activeMode) return;
    if (document.visibilityState !== "visible") return;
    await captureAndProcess();
  }, 500);
}

async function captureAndProcess() {
  isRequestPending = true;
  abortController = new AbortController();

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
    ctx.lineWidth = 6;
    ctx.strokeRect(f.x, f.y, f.w, f.h);

    ctx.fillStyle = color;
    ctx.font = "bold 24px Outfit, sans-serif";
    ctx.fillText(`${f.label.toUpperCase()}`, f.x, f.y - 15);
  });
}

/**
 * Handlers
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
      updateStatus(`Register: ${registerCount}/25`, true);
      if (elements.regStatus) elements.regStatus.textContent = `Captured ${registerCount} samples`;

      if (registerCount >= 25) {
        showToast("Registration Complete!", "success");
        activeMode = null;
        registerCount = 0;
        elements.regName.value = "";
        elements.regEmail.value = "";
        if (elements.regStatus) elements.regStatus.textContent = "New user registered";
        setBtnLoading(elements.btnRegister, false, `<span>Capture Face</span> <i class="ph ph-camera"></i>`);
      }
    }
  } catch (e) { }
}

function handleMatch(name) {
  verifiedCount++;
  if (elements.metricVerified) elements.metricVerified.textContent = verifiedCount;
  showToast(`Identity Verified: ${name}`, "success");
  if (elements.verifyResult) {
    elements.verifyResult.innerHTML = `<div style="color:#10b981; font-weight:700;">
      <i class="ph ph-check-circle"></i> VERIFIED: ${name.toUpperCase()}
    </div>`;
  }
  cancelVerify();
}

/**
 * Actions
 */
window.registerUser = () => {
  if (!elements.regName.value.trim()) return showToast("Please enter a name", "error");
  if (!isCamActive) return showToast("Start camera first", "info");
  activeMode = "register";
  registerCount = 0;
  updateStatus("Registration mode active", true);
  setBtnLoading(elements.btnRegister, true, "");
};

window.trainModel = async () => {
  const originalText = elements.btnTrain.innerHTML;
  setBtnLoading(elements.btnTrain, true, "");
  updateStatus("Training model...", true);

  try {
    const res = await fetch("/api/v1/train", { method: "POST" });
    const data = await res.json();
    showToast("AI Model Updated Successfully", "success");
    if (elements.metricModel) elements.metricModel.textContent = "Synced";
    if (elements.trainStatus) elements.trainStatus.textContent = "Model optimized";
  } catch (e) {
    showToast("Training failed", "error");
    if (elements.trainStatus) elements.trainStatus.textContent = "Sync failed";
  }
  finally {
    updateStatus("System Ready", isCamActive);
    setBtnLoading(elements.btnTrain, false, originalText);
  }
};

window.verifyFace = () => {
  if (!isCamActive) return showToast("Start camera first", "info");
  activeMode = "verify";
  if (elements.btnCancelVerify) elements.btnCancelVerify.style.display = "flex";
  updateStatus("Verification active", true);
  if (elements.verifyResult) elements.verifyResult.textContent = "Scanning face...";
};

window.cancelVerify = () => {
  activeMode = null;
  if (elements.btnCancelVerify) elements.btnCancelVerify.style.display = "none";
  if (elements.verifyResult) elements.verifyResult.textContent = "Awaiting input...";
  const ctx = elements.canvas.getContext("2d");
  ctx.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
  updateStatus("Camera Active", isCamActive);
};

// Start Up
getDevices();
if (navigator.mediaDevices.ondevicechange !== undefined) {
  navigator.mediaDevices.ondevicechange = getDevices;
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" && isCamActive) {
    // heavy throttling if needed
  }
});
