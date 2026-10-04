// script.js - the chat screen: sends messages to POST /api/chat and shows the reply + NLP details.
const $ = (id) => document.getElementById(id);
let employeeId = null;

const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
// very small formatter: **bold**, *italic*, new lines
const fmt = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/\n/g, "<br>");
const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function addMessage(text, who, time) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.innerHTML = fmt(text) + `<time>${time || now()}</time>`;
  $("messages").appendChild(div);
  $("messages").scrollTop = $("messages").scrollHeight;
}
function showError(text) { const b = $("banner"); b.textContent = text; b.hidden = !text; }
function setEnabled(on) { $("msg").disabled = !on; $("send").disabled = !on; document.querySelectorAll(".quick button").forEach((b) => (b.disabled = !on)); }

async function signIn(e) {
  e.preventDefault();
  const id = $("empId").value.trim().toUpperCase();
  showError("");
  try {
    const res = await fetch("/api/employee/" + encodeURIComponent(id));
    if (!res.ok) throw new Error((await res.json()).detail || "Employee not found");
    const emp = await res.json();
    employeeId = emp.employee_id;
    await fetch("/api/chat/reset/" + employeeId, { method: "POST" });   // fresh conversation
    $("messages").innerHTML = "";
    addMessage(`Hello ${emp.name.split(" ")[0]}! 👋 I'm your HR Assistant. How can I help you today?`, "bot");
    setEnabled(true);
    $("msg").focus();
  } catch (err) {
    employeeId = null; setEnabled(false);
    showError("Could not sign in: " + err.message + ". Try EMP101.");
  }
}

async function send(text) {
  text = text.trim();
  if (!employeeId) return showError("Please sign in with your Employee ID first.");
  if (!text) return;
  showError(""); addMessage(text, "user"); $("msg").value = "";
  $("typing").hidden = false; setEnabled(false);
  try {
    const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
                                           body: JSON.stringify({ employee_id: employeeId, message: text }) });
    if (!res.ok) throw new Error("Server returned " + res.status);
    const data = await res.json();
    addMessage(data.response, "bot", data.timestamp);
    showNlp(data);
  } catch (err) {
    showError("Could not reach the server. Please check that it is running and try again.");
  } finally {
    $("typing").hidden = true; setEnabled(true); $("msg").focus();
  }
}

function showNlp(d) {
  $("nlpEmpty").hidden = true; $("nlpBody").hidden = false;
  $("nIntent").textContent = d.intent + (d.context_used ? "  (from context)" : "");
  $("nConf").textContent = "Confidence: " + d.confidence.toFixed(2);
  $("nTop").textContent = "Top 3: " + d.top_intents.map((t) => `${t.intent} ${t.confidence.toFixed(2)}`).join(" | ");
  $("nTokens").textContent = d.tokens.join(" | ");
  $("nPos").innerHTML = d.pos_tags.map((p) => `<span>${esc(p.token)} <b>${p.pos}</b></span>`).join("");
  $("nNer").innerHTML = d.ner.length ? d.ner.map((n) => `<li>${esc(n.text)} → ${n.label}</li>`).join("") : "<li>none</li>";
  $("nEnt").textContent = Object.keys(d.entities).length ? JSON.stringify(d.entities, null, 1) : "none";
  $("nSent").textContent = `${d.sentiment} (score ${d.sentiment_score})`;
  $("nFlow").textContent = "Active flow: " + (d.flow || "none");
  $("nSlots").textContent = JSON.stringify(d.slots, null, 1);
}

$("login").addEventListener("submit", signIn);
$("composer").addEventListener("submit", (e) => { e.preventDefault(); send($("msg").value); });   // Enter key works via form submit
$("quick").addEventListener("click", (e) => { if (e.target.dataset.msg) send(e.target.dataset.msg); });
$("toggleNlp").addEventListener("click", (e) => {
  const on = e.target.getAttribute("aria-pressed") !== "true";
  e.target.setAttribute("aria-pressed", on);
  document.querySelector(".layout").classList.toggle("no-nlp", !on);
});
setEnabled(false);
signIn(new Event("submit"));      // auto sign-in with the default demo ID
