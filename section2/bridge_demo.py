from __future__ import annotations

from eth_account import Account

from agent_wallet_manager import AgentWalletManager
from monad_bridge import MonadBridge


def main() -> None:
    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()

    # Expects deployment artifact produced by scripts/deploy.js
    bridge = MonadBridge.from_deployment_file(manager.w3, "deployments/monadTestnet.json")

    master = Account.from_key(manager.master.private_key)
    worker = Account.from_key(manager.worker.private_key)

    print("Connected:", manager.summary())
    print("Contract address:", bridge.contract.address)

    # Example read call
    print("lockedFunds:", bridge.read("lockedFunds"))

    # Example write flow:
    # tx = bridge.send_contract_tx(master, "registerAgent", "Master", "orchestration")
    # print("registerAgent tx:", tx)
    # tx = bridge.send_contract_tx(worker, "registerAgent", "Worker", "execution")
    # print("registerAgent worker tx:", tx)


if __name__ == "__main__":
    main()
