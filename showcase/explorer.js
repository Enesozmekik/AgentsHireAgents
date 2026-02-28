const explorerBase = "https://testnet.monadscan.com/tx/";

const master = "0xa91625B029cE67100dEc0CE0d356E70337fE5082";
const worker = "0x08Db40CAb73737DED8B6D90cBEB7d661dc10cFc0";
const contract = "0x30e335f649d53fB885E83C6d2E3517B4E0E029AF";

const events = [
  {
    status: "Open",
    action: "Job Created",
    summary: "Master opened a new task for Worker and locked 1.00 MON in escrow.",
    from: master,
    to: contract,
    tx: "0xb6771cbe2a4821575a98ad73819df741c3eacae19f8e7ff4f5f1d56fa8823a94",
    badge: "Escrow Locked",
    escrow: "1.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.0000 MON",
  },
  {
    status: "Taken",
    action: "Job Accepted",
    summary: "Worker accepted the task. Timeout clock started.",
    from: worker,
    to: contract,
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
    from: worker,
    to: contract,
    tx: "0xc4c576f9d61578b85ea40287baae95b4892e64c2767c1de6ef4a728dcc02aa22",
    badge: "Delivery Posted",
    escrow: "1.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.0000 MON",
  },
  {
    status: "Resolved",
    action: "Work Approved",
    summary: "Master approved output. Escrow released to Worker (1% protocol fee retained).",
    from: master,
    to: contract,
    tx: "0x4d80914c12f8b3da568994edc7fd62e09b7240d4de77c8b32cadd3647b96fcd2",
    badge: "Payment Triggered",
    escrow: "0.0000 MON",
    masterDelta: "-1.0000 MON",
    workerDelta: "+0.9900 MON",
  },
];

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
  txLink.href = `${explorerBase}${event.tx}`;
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

render();
