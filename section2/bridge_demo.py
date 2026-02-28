from __future__ import annotations

from eth_account import Account

from agent_wallet_manager import AgentWalletManager
from monad_bridge import MonadBridge
from selection_engine import infer_category


def to_bytes32(category: str) -> bytes:
    raw = category.encode("utf-8")
    return raw + (b"\x00" * (32 - len(raw)))


def main() -> None:
    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()

    bridge = MonadBridge.from_deployment_file(manager.w3, "deployments/monadTestnet.json")

    master = Account.from_key(manager.master.private_key)
    worker = Account.from_key(manager.worker.private_key)

    print("Connected:", manager.summary())
    print("Contract address:", bridge.contract.address)
    print("lockedFunds:", bridge.read("lockedFunds"))

    # Example V2 read calls
    category = infer_category("Build a backend API for an agent marketplace")
    category_b32 = to_bytes32(category)
    print("Inferred category:", category)
    print("Category agents:", bridge.read("getCategoryAgents", category_b32))

    # Example write flow:
    # stake_wei = int(bridge.read("minRegistrationStakeWei"))
    # tx = bridge.send_contract_tx(master, "registerAgentV2", "Master", "orchestration", category_b32, 100000000000000, value_wei=stake_wei)
    # print("registerAgentV2 master tx:", tx)
    # tx = bridge.send_contract_tx(worker, "registerAgentV2", "Worker", "execution", category_b32, 100000000000000, value_wei=stake_wei)
    # print("registerAgentV2 worker tx:", tx)


if __name__ == "__main__":
    main()