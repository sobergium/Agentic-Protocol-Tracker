const flows = {
  authorization: {
    label: "Authorization-first",
    normal: ["payment_required","authorized","service_started","service_succeeded","settled","complete"],
    settlement: ["payment_required","authorized","service_started","service_succeeded","settlement_failed"],
    finality: ["payment_required","authorized","service_started","service_succeeded","settlement_pending"],
    replay: ["payment_required","replay_rejected"]
  },
  upfront: {
    label: "Upfront settlement",
    normal: ["payment_required","authorized","settled","service_started","service_succeeded","complete"],
    settlement: ["payment_required","authorized","settlement_failed"],
    finality: ["payment_required","authorized","settlement_pending"],
    replay: ["payment_required","replay_rejected"]
  },
  escrow: {
    label: "Escrow",
    normal: ["payment_required","authorized","funds_locked","service_started","service_succeeded","released","complete"],
    settlement: ["payment_required","authorized","funds_locked","service_started","service_succeeded","settlement_failed"],
    finality: ["payment_required","authorized","settlement_pending"],
    replay: ["payment_required","replay_rejected"]
  }
};
const descriptions = {
  complete:["Complete","Payment and service both reached terminal success.","success"],
  replay_rejected:["Replay rejected","The proof fingerprint was reserved before service execution. No duplicate work ran.","failure"],
  settlement_failed:["Settlement failed","The audit trail preserves whether service had already succeeded at the failure boundary.","failure"],
  settlement_pending:["Finality indeterminate","The timeout is not proof of failure. Reconciliation must precede any service retry.","pending"]
};
let selectedFlow = "authorization";
let lastEvents = [];
const timeline = document.querySelector("#timeline");
const log = document.querySelector("#log");
const outcome = document.querySelector("#outcome");
const run = document.querySelector("#run");

document.querySelectorAll("[data-flow]").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-flow]").forEach(item => item.classList.remove("selected"));
    button.classList.add("selected");
    selectedFlow = button.dataset.flow;
    document.querySelector("#flow-label").textContent = flows[selectedFlow].label;
    reset();
  });
});

function reset(){
  timeline.innerHTML = "";
  log.innerHTML = '<p class="empty-log">Run a transaction to generate evidence.</p>';
  outcome.className = "outcome";
  outcome.innerHTML = '<span class="outcome-label">Ready</span><strong>Select a scenario and run the transaction.</strong><p>The state machine will expose the exact point where payment and service diverge.</p>';
  lastEvents = [];
}

function title(state){
  return state.split("_").map(word => word[0].toUpperCase()+word.slice(1)).join(" ");
}

function renderLog(events){
  log.innerHTML = events.map(event =>
    '<div class="log-row"><span>'+String(event.sequence).padStart(2,"0")+'</span>'+
    '<code>'+event.from+' → '+event.to+'</code>'+
    '<span>'+event.evidence+'</span></div>'
  ).join("");
}

run.addEventListener("click", async () => {
  run.disabled = true;
  timeline.innerHTML = "";
  const scenario = document.querySelector('input[name="scenario"]:checked').value;
  const states = flows[selectedFlow][scenario];
  let previous = "created";
  lastEvents = [];
  for (let index=0; index<states.length; index++){
    const state = states[index];
    const node = document.createElement("div");
    const terminalClass = state.includes("failed") || state.includes("rejected") ? "failure" : state.includes("pending") ? "pending" : "success";
    node.className = "state "+terminalClass;
    node.textContent = title(state);
    timeline.appendChild(node);
    await new Promise(resolve => setTimeout(resolve, 170));
    node.classList.add("show");
    lastEvents.push({
      sequence:index+1,
      from:previous,
      to:state,
      evidence:state === "authorized" ? "proof_reserved=true" :
        state === "service_succeeded" ? "service_receipt=recorded" :
        state === "settlement_pending" ? "terminal=false" :
        state.includes("failed") ? "compensation_required=true" : "recorded=true"
    });
    previous = state;
    renderLog(lastEvents);
  }
  const final = states.at(-1);
  const [heading,copy,kind] = descriptions[final] || descriptions.complete;
  outcome.className = "outcome "+(kind === "success" ? "" : kind);
  outcome.innerHTML = '<span class="outcome-label">'+title(final)+'</span><strong>'+heading+'</strong><p>'+copy+'</p>';
  run.disabled = false;
});

document.querySelector("#copy-log").addEventListener("click", async event => {
  if (!lastEvents.length) return;
  await navigator.clipboard.writeText(JSON.stringify(lastEvents,null,2));
  const original = event.target.textContent;
  event.target.textContent = "Copied";
  setTimeout(()=>event.target.textContent=original,1200);
});
