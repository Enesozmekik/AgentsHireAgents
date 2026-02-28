const explorerBaseFallback = "https://testnet.monadscan.com/tx";

const staticEvents = [
  {
    status: "Open",
    action: "Job Created",
    summary: "Master opened a new task for Worker and locked 1.00 MON in escrow.",
    from: "0xa91625B029cE67100dEc0CE0d356E70337fE5082",
    to: "0xFA87ee879375bb43d414387d3De1D899ea20fe0F",
    tx: "0xb6771cbe2a4821575a98ad73819df741c3eacae19f8e7ff4f5f1d56fa8823a94",
    badge: "Escrow Locked",
    escrow: "1.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.0000 MON",
  },
  {
    status: "Taken",
    action: "Job Accepted",
    summary: "Worker accepted the task.",
    from: "0x0CACF914624BBe5c43c45727b877806C461fAf02",
    to: "0xFA87ee879375bb43d414387d3De1D899ea20fe0F",
    tx: "0xe533d1649dbd6c6b1659013603f349cf29b8dc2cc3fec0584b82f4e6191cd897",
    badge: "State Update",
    escrow: "1.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.0000 MON",
  },
  {
    status: "Submitted",
    action: "Work Submitted",
    summary: "Worker submitted delivery payload (mock JSON output) on-chain.",
    from: "0x0CACF914624BBe5c43c45727b877806C461fAf02",
    to: "0xFA87ee879375bb43d414387d3De1D899ea20fe0F",
    tx: "0xc4c576f9d61578b85ea40287baae95b4892e64c2767c1de6ef4a728dcc02aa22",
    badge: "Delivery Posted",
    escrow: "1.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.0000 MON",
  },
  {
    status: "Resolved",
    action: "Work Approved",
    summary: "Master approved output. Escrow released to Worker.",
    from: "0xa91625B029cE67100dEc0CE0d356E70337fE5082",
    to: "0xFA87ee879375bb43d414387d3De1D899ea20fe0F",
    tx: "0x4d80914c12f8b3da568994edc7fd62e09b7240d4de77c8b32cadd3647b96fcd2",
    badge: "Payment Triggered",
    escrow: "0.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.9900 MON",
  },
];

let events = staticEvents;
let explorerBase = explorerBaseFallback;
let current = 0;
let autoTimer = null;

const timeline = document.getElementById("timeline");
const stateStatus = document.getElementById("state-status");
const stateEscrow = document.getElementById("state-escrow");
const stateMaster = document.getElementById("state-master");
const stateWorker = document.getElementById("state-worker");
const txAction = document.getElementById("tx-action");
const txFrom = document.getElementById("tx-from");
const txTo = document.getElementById("tx-to");
const txHash = document.getElementById("tx-hash");
const txLink = document.getElementById("tx-link");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const autoBtn = document.getElementById("auto-btn");

function short(address) {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function renderTimeline() {
  timeline.innerHTML = events
    .map((event, idx) => {
      const active = idx === current ? "active" : "";
      return `
        <li class="${active}" data-step="${idx}">
          <div class="row">
            <strong>${idx + 1}. ${event.action}</strong>
            <span class="badge">${event.badge}</span>
          </div>
          <p class="sub">${event.summary}</p>
          <div class="sub">${short(event.from)} -> ${short(event.to)}</div>
          <code class="hash">${event.tx}</code>
        </li>
      `;
    })
    .join("");

  [...timeline.querySelectorAll("li")].forEach((item) => {
    item.addEventListener("click", () => {
      current = Number(item.dataset.step);
      render();
    });
  });
}

function renderState() {
  const event = events[current];
  stateStatus.textContent = event.status;
  stateEscrow.textContent = event.escrow;
  stateMaster.textContent = event.masterDelta;
  stateWorker.textContent = event.workerDelta;

  txAction.textContent = event.action;
  txFrom.textContent = event.from;
  txTo.textContent = event.to;
  txHash.textContent = event.tx;
  txLink.href = `${explorerBase}/${event.tx}`;
}

function render() {
  renderTimeline();
  renderState();
}

function next() {
  current = (current + 1) % events.length;
  render();
}

prevBtn.addEventListener("click", () => {
  current = (current - 1 + events.length) % events.length;
  render();
});

nextBtn.addEventListener("click", next);

autoBtn.addEventListener("click", () => {
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    autoBtn.textContent = "Auto Play";
    return;
  }

  autoTimer = setInterval(next, 2500);
  autoBtn.textContent = "Stop";
});

async function loadDemoData() {
  try {
    const res = await fetch("./demo-data.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const taskBudget = data.task?.budgetEth || "0.0";
    const selected = data.selectionProof?.selectedAgent || "0x0000000000000000000000000000000000000000";
    const contract = data.network?.contractAddress || "0x0000000000000000000000000000000000000000";
    explorerBase = data.network?.explorerTxBase || explorerBase;

    const statusMap = ["Open", "Taken", "Submitted", "Resolved", "Resolved"];
    const badgeMap = ["Escrow Locked", "State Update", "Delivery Posted", "Payment Triggered", "Feedback Updated"];
    events = (data.workflow?.steps || []).map((step, idx) => ({
      status: statusMap[idx] || "Resolved",
      action: step.key,
      summary: step.label,
      from: idx === 0 || idx === 3 || idx === 4 ? "MASTER" : selected,
      to: contract,
      tx: step.txHash || "-",
      badge: badgeMap[idx] || "Step",
      escrow: idx < 3 ? `${taskBudget} MON` : "0.0000 MON",
      masterDelta: `-${taskBudget} MON`,
      workerDelta: idx < 3 ? "+0.0000 MON" : "+settled",
    }));

    if (!events.length) {
      events = staticEvents;
    }
  } catch {
    events = staticEvents;
  }
}

(async function init() {
  await loadDemoData();
  render();
})();
