from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3


@dataclass(frozen=True)
class AgentWallet:
    role: str
    private_key: str
    address: str


class AgentWalletManager:
    def __init__(self, rpc_url: str, master_private_key: str, worker_private_key: str) -> None:
        if not rpc_url:
            raise ValueError("MONAD_RPC_URL is required")
        if not master_private_key:
            raise ValueError("MASTER_PRIVATE_KEY is required")
        if not worker_private_key:
            raise ValueError("WORKER_PRIVATE_KEY is required")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.master = self._make_wallet("MASTER", master_private_key)
        self.worker = self._make_wallet("WORKER", worker_private_key)

    @classmethod
    def from_env(cls) -> "AgentWalletManager":
        root_env = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path=root_env if root_env.exists() else None)
        file_vals = _read_env_fallback(root_env)
        return cls(
            rpc_url=(os.getenv("MONAD_RPC_URL") or file_vals.get("MONAD_RPC_URL", "")).strip(),
            master_private_key=(os.getenv("MASTER_PRIVATE_KEY") or file_vals.get("MASTER_PRIVATE_KEY", "")).strip(),
            worker_private_key=(os.getenv("WORKER_PRIVATE_KEY") or file_vals.get("WORKER_PRIVATE_KEY", "")).strip(),
        )

    def _make_wallet(self, role: str, private_key: str) -> AgentWallet:
        account = Account.from_key(private_key)
        return AgentWallet(role=role, private_key=private_key, address=account.address)

    def assert_rpc_connection(self) -> None:
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to MONAD RPC")

    def summary(self) -> dict:
        chain_id = self.w3.eth.chain_id if self.w3.is_connected() else None
        return {
            "rpc_connected": self.w3.is_connected(),
            "chain_id": chain_id,
            "master_address": self.master.address,
            "worker_address": self.worker.address,
        }


def _read_env_fallback(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    raw = env_path.read_text(encoding="utf-8-sig", errors="ignore")
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


if __name__ == "__main__":
    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()
    print(manager.summary())
