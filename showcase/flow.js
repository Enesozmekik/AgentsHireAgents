const staticSteps = [
  {
    title: "Step 1: Job Created",
    desc: "Master sends createJob() and the budget is escrow-locked on-chain.",
    tx: "createJob()",
    hash: "0xb6771cbe2a4821575a98ad73819df741c3eacae19f8e7ff4f5f1d56fa8823a94",
  },
  {
    title: "Step 2: Worker Accepts",
    desc: "Worker calls acceptJob(), switching state from Open to Taken.",
    tx: "acceptJob()",
    hash: "0xe533d1649dbd6c6b1659013603f349cf29b8dc2cc3fec0584b82f4e6191cd897",
  },
  {
    title: "Step 3: Work Submitted",
    desc: "MockWorkerLogic generates JSON output and submitWork() records delivery.",
    tx: "submitWork()",
    hash: "0xc4c576f9d61578b85ea40287baae95b4892e64c2767c1de6ef4a728dcc02aa22",
  },
  {
    title: "Step 4: Master Approves",
    desc: "Master validates output and approves job completion.",
    tx: "approveWork()",
    hash: "0x4d80914c12f8b3da568994edc7fd62e09b7240d4de77c8b32cadd3647b96fcd2",
  },
  {
    title: "Step 5: Settlement Finalized",
    desc: "Worker receives payout and job status reaches Resolved.",
    tx: "payment transfer",
    hash: "0x4d80914c12f8b3da568994edc7fd62e09b7240d4de77c8b32cadd3647b96fcd2",
  },
];

let steps = staticSteps;
let explorerBase = "https://testnet.monadscan.com/tx";
let current = 0;
let toastTimer = null;

const title = document.getElementById("step-title");
const desc = document.getElementById("step-desc");
const tx = document.getElementById("step-tx");
const button = document.getElementById("next-btn");
const nodes = [...document.querySelectorAll(".node")];
const progressFill = document.getElementById("progress-fill");
const progressDot = document.getElementById("progress-dot");
const stepHash = document.getElementById("step-hash");
const copyHashBtn = document.getElementById("copy-hash-btn");
const txLink = document.getElementById("tx-link");
const toast = document.getElementById("tx-toast");
const toastStep = document.getElementById("toast-step");
const toastHash = document.getElementById("toast-hash");

function showToast() {
  toast.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.classList.remove("show");
  }, 2200);
}

function renderStep(index) {
  const step = steps[index];
  const percent = (index / (steps.length - 1)) * 100;

  progressFill.style.width = `${percent}%`;
  progressDot.style.left = `${percent}%`;

  title.textContent = step.title;
  desc.textContent = step.desc;
  tx.textContent = step.tx;
  stepHash.textContent = step.hash;
  txLink.href = `${explorerBase}/${step.hash}`;

  nodes.forEach((node) => node.classList.remove("active"));
  const activeNode = nodes.find((n) => Number(n.dataset.step) === index);
  if (activeNode) activeNode.classList.add("active");

  toastStep.textContent = step.title;
  toastHash.textContent = step.hash;
  showToast();
}

button.addEventListener("click", () => {
  current = (current + 1) % steps.length;
  renderStep(current);
});

nodes.forEach((node) => {
  node.addEventListener("click", () => {
    current = Number(node.dataset.step);
    renderStep(current);
  });
});

copyHashBtn.addEventListener("click", async () => {
  const value = steps[current].hash;
  try {
    await navigator.clipboard.writeText(value);
    copyHashBtn.textContent = "Copied";
    setTimeout(() => {
      copyHashBtn.textContent = "Copy Hash";
    }, 1000);
  } catch {
    copyHashBtn.textContent = "Copy Failed";
    setTimeout(() => {
      copyHashBtn.textContent = "Copy Hash";
    }, 1000);
  }
});

async function loadDemoData() {
  try {
    const res = await fetch("./demo-data.json", { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    const flowSteps = (data.workflow?.steps || []).map((item, idx) => ({
      title: `Step ${idx + 1}: ${item.label}`,
      desc: item.label,
      tx: item.key,
      hash: item.txHash || "-",
    }));
    if (flowSteps.length > 0) {
      steps = flowSteps;
      explorerBase = data.network?.explorerTxBase || explorerBase;
    }
  } catch {
    // keep fallback
  }
}

(async function init() {
  await loadDemoData();
  renderStep(current);
})();
