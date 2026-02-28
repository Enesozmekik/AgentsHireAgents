const CATEGORY_KEYWORDS = {
  DEVELOPMENT: ["code", "api", "contract", "backend", "frontend", "integration", "debug"],
  RESEARCH: ["research", "analyze", "report", "trend", "market", "review"],
  DATA_MINING: ["data", "scrape", "dataset", "extract", "pipeline", "etl"],
  CONTENT_GEN: ["content", "write", "post", "summary", "copy", "article"],
};

const FALLBACK_DATA = {
  generatedAt: "2026-02-28T17:50:00Z",
  network: {
    chainId: 10143,
    contractAddress: "0xFA87ee879375bb43d414387d3De1D899ea20fe0F",
    explorerTxBase: "https://testnet.monadscan.com/tx",
  },
  task: {
    prompt: "Build a post-demo backend selection bridge and summarize final run.",
    category: "DEVELOPMENT",
    budgetWei: 1000000000000000,
    budgetEth: "0.001",
    jobId: 0,
  },
  ranking: [
    { address: "0x0CACF914624BBe5c43c45727b877806C461fAf02", category: "DEVELOPMENT", baseFeeWei: 80000000000000, reputation: 45 },
    { address: "0x08Db40CAb73737DED8B6D90cBEB7d661dc10cFc0", category: "DEVELOPMENT", baseFeeWei: 100000000000000, reputation: 52 },
    { address: "0x081d7E83E82688B496a2E0387E469ee9DE05fc65", category: "DEVELOPMENT", baseFeeWei: 150000000000000, reputation: 75 },
    { address: "0xa91625B029cE67100dEc0CE0d356E70337fE5082", category: "DEVELOPMENT", baseFeeWei: 100000000000000, reputation: 50 },
    { address: "0xCf451a6a391Ac37cAb6141ff07937bD56D67cdb6", category: "DEVELOPMENT", baseFeeWei: 250000000000000, reputation: 92 },
    { address: "0x32c2d71Da20DC0a60B1D8ec9ca98ED613ad56815", category: "RESEARCH", baseFeeWei: 80000000000000, reputation: 45 },
    { address: "0x76c5745c993aBA5d556EBAB1EAA71a9FFe002A3C", category: "RESEARCH", baseFeeWei: 150000000000000, reputation: 75 },
    { address: "0x7A8Dee3cA20c79A848498FC6c72E43abe4e6E9C7", category: "RESEARCH", baseFeeWei: 250000000000000, reputation: 92 },
    { address: "0x767c59FaA0708df8E04FD6d7575dcBc9AD383B89", category: "DATA_MINING", baseFeeWei: 80000000000000, reputation: 45 },
    { address: "0x37e565C9228a99861797F0a5F4676f1F98270670", category: "DATA_MINING", baseFeeWei: 150000000000000, reputation: 75 },
    { address: "0x44Ea66047f250A32C9BE39f6E54A3eae56D7e600", category: "DATA_MINING", baseFeeWei: 250000000000000, reputation: 92 },
    { address: "0x58257910AFbE81f9cB61869222a8C87702DDDf6b", category: "CONTENT_GEN", baseFeeWei: 80000000000000, reputation: 45 },
    { address: "0xC6afcE39a04A103E9270Fa75015E30013d927Ba9", category: "CONTENT_GEN", baseFeeWei: 150000000000000, reputation: 75 },
    { address: "0xC953ECB6aBd87fd3d7f04A76A7723f3bB54499dd", category: "CONTENT_GEN", baseFeeWei: 250000000000000, reputation: 92 },
  ],
  selectionProof: {
    selectedAgent: "0x0CACF914624BBe5c43c45727b877806C461fAf02",
    reason: "Selected the highest quality (reputation) within budget; ties prefer lower base fee.",
  },
  workflow: {
    steps: [
      { key: "createJobByCategory", label: "Budget escrow locked", txHash: "0xb6771cbe2a4821575a98ad73819df741c3eacae19f8e7ff4f5f1d56fa8823a94" },
      { key: "acceptJob", label: "Worker accepted the job", txHash: "0xe533d1649dbd6c6b1659013603f349cf29b8dc2cc3fec0584b82f4e6191cd897" },
      { key: "submitWork", label: "Worker submitted delivery proof", txHash: "0xc4c576f9d61578b85ea40287baae95b4892e64c2767c1de6ef4a728dcc02aa22" },
      { key: "releasePayment", label: "Payment released to worker", txHash: "0x4d80914c12f8b3da568994edc7fd62e09b7240d4de77c8b32cadd3647b96fcd2" },
      { key: "applySyntheticFeedback", label: "Reputation feedback applied", txHash: "0x2e9ca224b19b91ee8f3a1b8d70a695861af533b3068e1c77e95d7ff0a8d742b6" },
    ],
  },
};

function inferCategory(prompt) {
  const lowered = (prompt || "").toLowerCase();
  for (const [category, words] of Object.entries(CATEGORY_KEYWORDS)) {
    if (words.some((word) => lowered.includes(word))) {
      return category;
    }
  }
  return "RESEARCH";
}

function efficiency(item) {
  if (!item.baseFeeWei) return 0;
  return item.reputation / Number(item.baseFeeWei);
}

function compareByQualityThenPrice(a, b) {
  if (a.reputation !== b.reputation) return b.reputation - a.reputation;

  const feeA = Number(a.baseFeeWei || 0);
  const feeB = Number(b.baseFeeWei || 0);
  if (feeA !== feeB) return feeA - feeB;

  return efficiency(b) - efficiency(a);
}

function shortAddr(value) {
  if (!value || value.length < 12) return value || "-";
  return `${value.slice(0, 6)}...${value.slice(-4)}`;
}

function mono(value) {
  return Number(value).toLocaleString("en-US");
}

async function loadData() {
  try {
    const res = await fetch("./demo-data.json", { cache: "no-store" });
    if (!res.ok) throw new Error("demo-data.json not found");
    const payload = await res.json();
    return payload;
  } catch {
    return FALLBACK_DATA;
  }
}

function renderMeta(data) {
  document.getElementById("meta-contract").textContent = shortAddr(data.network.contractAddress);
  document.getElementById("meta-chain").textContent = String(data.network.chainId);
  document.getElementById("meta-generated").textContent = new Date(data.generatedAt).toLocaleString();
}

function renderRanking(ranking, selectedAgent) {
  const body = document.getElementById("ranking-body");
  const badge = document.getElementById("ranking-badge");
  badge.textContent = `${ranking.length} candidates`;
  body.innerHTML = ranking
    .map((item, idx) => {
      const eff = efficiency(item);
      const isActive = item.address.toLowerCase() === (selectedAgent || "").toLowerCase();
      return `
        <tr class="${isActive ? "active" : ""}">
          <td>${idx + 1}</td>
          <td>${shortAddr(item.address)}</td>
          <td>${item.reputation}</td>
          <td>${mono(item.baseFeeWei)}</td>
          <td>${eff.toExponential(3)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderProof(task, proof) {
  document.getElementById("selected-agent").textContent = shortAddr(proof.selectedAgent || "-");
  document.getElementById("proof").textContent = proof.reason || "No selection reason available.";
  document.getElementById("proof-budget").textContent = `${task.budgetEth} MON (${mono(task.budgetWei)} wei)`;
  document.getElementById("proof-job-id").textContent = task.jobId == null ? "pending" : String(task.jobId);
}

function renderTimeline(steps, explorerBase, doneCount = 0) {
  const root = document.getElementById("timeline");
  root.innerHTML = steps
    .map((step, idx) => {
      const done = idx < doneCount;
      const hash = step.txHash || "(pending)";
      const link = hash.startsWith("0x") ? `${explorerBase}/${hash}` : "#";
      return `
        <li class="${done ? "done" : ""}">
          <div class="t-head">
            <strong>${idx + 1}. ${step.label}</strong>
            <span>${done ? "done" : "waiting"}</span>
          </div>
          <div class="t-hash">${hash}</div>
          ${hash.startsWith("0x") ? `<a href="${link}" target="_blank" rel="noreferrer">Explorer</a>` : ""}
        </li>
      `;
    })
    .join("");
}

function computeSelection(data, formValue) {
  const category = formValue.category === "AUTO" ? inferCategory(formValue.prompt) : formValue.category;
  const budgetWei = BigInt(Math.floor(Number(formValue.budget) * 1e18));

  const ranking = data.ranking
    .filter((item) => item.category === category && BigInt(item.baseFeeWei) <= budgetWei)
    .sort(compareByQualityThenPrice);

  const selected = ranking[0] || null;
  const reason = selected
    ? `Agent ${selected.address} selected because it has the highest quality score (reputation) within this category and budget; ties prefer lower base fee.`
    : "No eligible agent found within budget.";

  return {
    task: {
      prompt: formValue.prompt,
      category,
      budgetWei: budgetWei.toString(),
      budgetEth: String(formValue.budget),
      jobId: data.task.jobId,
    },
    ranking,
    selectionProof: {
      selectedAgent: selected?.address || "-",
      reason,
    },
    workflow: data.workflow,
    network: data.network,
  };
}

function mountReveal() {
  const nodes = [...document.querySelectorAll(".reveal")];
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("visible");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.1 });
  nodes.forEach((node, i) => {
    node.style.transitionDelay = `${i * 50}ms`;
    observer.observe(node);
  });
}

(async function init() {
  mountReveal();
  const data = await loadData();

  document.getElementById("prompt").value = data.task.prompt || "";
  document.getElementById("category").value = data.task.category || "AUTO";
  document.getElementById("budget").value = data.task.budgetEth || "0.01";

  renderMeta(data);
  renderRanking(data.ranking, data.selectionProof.selectedAgent);
  renderProof(data.task, data.selectionProof);
  renderTimeline(data.workflow.steps, data.network.explorerTxBase, data.workflow.steps.length);

  const playBtn = document.getElementById("play-flow");
  playBtn.addEventListener("click", () => {
    let i = 0;
    renderTimeline(data.workflow.steps, data.network.explorerTxBase, 0);
    const timer = setInterval(() => {
      i += 1;
      renderTimeline(data.workflow.steps, data.network.explorerTxBase, i);
      if (i >= data.workflow.steps.length) {
        clearInterval(timer);
      }
    }, 900);
  });

  document.getElementById("task-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const selected = computeSelection(data, {
      prompt: document.getElementById("prompt").value,
      category: document.getElementById("category").value,
      budget: document.getElementById("budget").value,
    });

    renderRanking(selected.ranking, selected.selectionProof.selectedAgent);
    renderProof(selected.task, selected.selectionProof);
    renderTimeline(selected.workflow.steps, selected.network.explorerTxBase, 0);
  });
})();
