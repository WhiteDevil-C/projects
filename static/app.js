const statusText = document.getElementById("statusText");
const toastEl = document.getElementById("toast");
const trainStatus = document.getElementById("trainStatus");
const verifyResult = document.getElementById("verifyResult");
const awardResult = document.getElementById("awardResult");

function toast(msg){
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(()=>toastEl.classList.remove("show"), 1800);
}

function setStatus(msg, ok=true){
  statusText.textContent = msg;
  const dot = document.getElementById("statusDot");
  dot.style.background = ok ? "#63ffb0" : "#ff5a7a";
  dot.style.boxShadow = ok ? "0 0 14px rgba(99,255,176,.55)" : "0 0 14px rgba(255,90,122,.55)";
}

async function postJSON(url, body){
  const res = await fetch(url, {
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(()=> ({}));
  if(!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function setDisabled(disabled){
  document.querySelectorAll("button").forEach(b => b.disabled = disabled);
}

function openHelp(){ document.getElementById("helpModal").classList.add("show"); }
function closeHelp(){ document.getElementById("helpModal").classList.remove("show"); }
window.openHelp = openHelp;
window.closeHelp = closeHelp;

function setMetric(id, val){ const el = document.getElementById(id); if(el) el.textContent = val; }

// Simple local metrics (not from DB; just UX)
let metricUsersCount = 0;
let metricAwardsCount = 0;
let modelTrained = false;
setMetric("metricUsers", "0");
setMetric("metricAwards", "0");
setMetric("metricModel", "Not trained");

async function registerUser(){
  const name = document.getElementById("regName").value.trim();
  const email = document.getElementById("regEmail").value.trim();

  if(!name) return toast("Enter your name first");

  setDisabled(true);
  setStatus("Registering...", true);
  toast("Opening camera for capture...");

  try{
    const data = await postJSON("/api/register", { name, email });
    metricUsersCount += 1;
    setMetric("metricUsers", String(metricUsersCount));
    toast(`Captured samples ✅ (${data.captured ?? "done"})`);
    setStatus("Ready", true);
  }catch(e){
    toast(e.message);
    setStatus("Ready", false);
  }finally{
    setDisabled(false);
  }
}

async function trainModel(){
  setDisabled(true);
  setStatus("Training model...", true);
  toast("Training LBPH model...");

  try{
    await postJSON("/api/train", {});
    modelTrained = true;
    setMetric("metricModel", "Trained ✅");
    trainStatus.textContent = "Model trained ✅ You can verify now.";
    toast("Model trained ✅");
    setStatus("Ready", true);
  }catch(e){
    toast(e.message);
    setStatus("Ready", false);
  }finally{
    setDisabled(false);
  }
}

async function verifyFace(){
  setDisabled(true);
  setStatus("Verifying...", true);
  toast("Opening camera for verification...");

  try{
    const data = await postJSON("/api/verify", {});
    if(data.matched){
      verifyResult.textContent = `Matched ✅ Name: ${data.name} | Confidence: ${data.confidence ?? "N/A"}`;
      document.getElementById("awardName").value = data.name;
      toast(`Welcome ${data.name} 🎉`);
    }else{
      verifyResult.textContent = "No match ❌ Try again (better light / face centered).";
      toast("Not matched");
    }
    setStatus("Ready", true);
  }catch(e){
    toast(e.message);
    setStatus("Ready", false);
  }finally{
    setDisabled(false);
  }
}

async function generateAward(){
  const name = document.getElementById("awardName").value.trim();
  const award_title = document.getElementById("awardTitle").value.trim() || "Certificate of Achievement";

  if(!name) return toast("Verify first or type name");

  setDisabled(true);
  setStatus("Generating certificate...", true);
  toast("Creating certificate...");

  try{
    const data = await postJSON("/api/award", { name, award_title });
    metricAwardsCount += 1;
    setMetric("metricAwards", String(metricAwardsCount));
    awardResult.innerHTML = `Certificate created ✅ <a href="${data.download_url}" target="_blank">Download</a>`;
    toast("Certificate ready 🎓");
    setStatus("Ready", true);
  }catch(e){
    toast(e.message);
    setStatus("Ready", false);
  }finally{
    setDisabled(false);
  }
}

window.registerUser = registerUser;
window.trainModel = trainModel;
window.verifyFace = verifyFace;
window.generateAward = generateAward;
