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


const trackerState = { catalog: null };

function humanize(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}

function sourceStatus(entity) {
  const statuses = entity.sources.map(source => source.scanStatus);
  if (statuses.includes("ok")) return "ok";
  if (statuses.includes("restricted")) return "restricted";
  return statuses[0] || "not_scanned";
}

function optionList(select, values) {
  for (const value of [...values].sort()) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = humanize(value);
    select.appendChild(option);
  }
}

function renderTracker() {
  const catalog = trackerState.catalog;
  if (!catalog) return;
  const query = document.querySelector("#tracker-search").value.trim().toLowerCase();
  const domain = document.querySelector("#domain-filter").value;
  const type = document.querySelector("#type-filter").value;
  const status = document.querySelector("#status-filter").value;
  const rows = catalog.entities.filter(entity => {
    const haystack = [entity.name, entity.type, entity.steward, entity.jurisdiction, ...entity.domains].join(" ").toLowerCase();
    return (!query || haystack.includes(query)) &&
      (!domain || entity.domains.includes(domain)) &&
      (!type || entity.type === type) &&
      (!status || sourceStatus(entity) === status);
  });
  document.querySelector("#result-count").textContent = rows.length + " of " + catalog.counts.entities + " systems";
  document.querySelector("#tracker-results").innerHTML = rows.length ? rows.map(entity => {
    const evidence = entity.sources.map(source =>
      '<a href="' + source.canonicalUrl + '" target="_blank" rel="noreferrer">' +
      '<i class="status-dot ' + source.scanStatus + '"></i>' +
      (source.scanStatus === "ok" ? "Primary source" : humanize(source.scanStatus)) + ' ↗</a>'
    ).join("");
    return '<article class="tracker-row" role="row">' +
      '<div><strong>' + entity.name + '</strong><small>' + entity.steward + ' · ' + entity.jurisdiction + '</small></div>' +
      '<span class="entity-type">' + humanize(entity.type) + '</span>' +
      '<div class="domain-tags">' + entity.domains.map(item => '<span>' + humanize(item) + '</span>').join("") + '</div>' +
      '<div class="source-links">' + evidence + '</div></article>';
  }).join("") : '<p class="tracker-empty">No systems match these filters.</p>';
}

async function loadTracker() {
  try {
    const response = await fetch("generated/catalog.json", { cache: "no-store" });
    if (!response.ok) throw new Error("catalog unavailable");
    const catalog = await response.json();
    trackerState.catalog = catalog;
    document.querySelector("#metric-entities").textContent = catalog.counts.entities;
    document.querySelector("#metric-sources").textContent = catalog.counts.sources;
    document.querySelector("#metric-domains").textContent = catalog.counts.domains;
    document.querySelector("#metric-errors").textContent = catalog.counts.errors;
    document.querySelector("#scanned-count").textContent = catalog.counts.scanned;
    document.querySelector("#restricted-count").textContent = catalog.counts.restricted || 0;
    optionList(document.querySelector("#domain-filter"), new Set(catalog.domains));
    optionList(document.querySelector("#type-filter"), new Set(catalog.entities.map(entity => entity.type)));
    renderTracker();
  } catch (error) {
    document.querySelector("#tracker-results").innerHTML = '<p class="tracker-empty">The evidence catalog could not be loaded. View the repository audit data for status.</p>';
    document.querySelector("#result-count").textContent = "Catalog unavailable";
  }
}

["tracker-search", "domain-filter", "type-filter", "status-filter"].forEach(id => {
  document.querySelector("#" + id).addEventListener("input", renderTracker);
});
loadTracker();
