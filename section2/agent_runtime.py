from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3


@dataclass(frozen=True)
class SyntheticAgent:
    address: str
    private_key: str
    name: str
    category_hex: str
    base_fee_wei: int
    reputation: int


class AgentRuntime:
    def __init__(self, w3: Web3, synthetic_agents_file: str | Path = "section2/synthetic_agents.private.json") -> None:
        self.w3 = w3
        self.synthetic_agents_file = Path(synthetic_agents_file)
        self._agents_by_address: dict[str, SyntheticAgent] = {}
        self._load_agents()

    def _load_agents(self) -> None:
        if not self.synthetic_agents_file.exists():
            legacy = Path("section2/synthetic_agents.json")
            if legacy.exists():
                self.synthetic_agents_file = legacy
            else:
                raise FileNotFoundError(f"Synthetic agents file not found: {self.synthetic_agents_file}")

        payload = json.loads(self.synthetic_agents_file.read_text(encoding="utf-8"))
        agents = payload.get("agents", [])
        for raw in agents:
            address = Web3.to_checksum_address(raw["address"])
            private_key = raw["private_key"]
            if not private_key.startswith("0x"):
                private_key = f"0x{private_key}"
            agent = SyntheticAgent(
                address=address,
                private_key=private_key,
                name=raw.get("name", "synthetic"),
                category_hex=raw.get("category_hex", ""),
                base_fee_wei=int(raw.get("base_fee_wei", 0)),
                reputation=int(raw.get("reputation", 0)),
            )
            self._agents_by_address[address.lower()] = agent

    def get_synthetic_account(self, address: str) -> LocalAccount:
        key = Web3.to_checksum_address(address).lower()
        agent = self._agents_by_address.get(key)
        if agent is None:
            raise KeyError(f"Selected worker {address} is not present in synthetic agent key file")
        return Account.from_key(agent.private_key)

    def ensure_agent_gas(
        self,
        funder: LocalAccount,
        target_address: str,
        min_balance_wei: int = 0,
        max_tx_gas: int = 800_000,
        tx_buffer_count: int = 3,
    ) -> str | None:
        target = Web3.to_checksum_address(target_address)
        current = self.w3.eth.get_balance(target)
        gas_price = self.w3.eth.gas_price
        required_for_tx = gas_price * max_tx_gas * tx_buffer_count
        required_balance = max(min_balance_wei, required_for_tx)

        if required_balance <= 0:
            required_balance = 5_000_000_000_000_000

        if current >= required_balance:
            return None

        topup_wei = required_balance - current

        nonce = self.w3.eth.get_transaction_count(funder.address, block_identifier="pending")
        tx = {
            "chainId": self.w3.eth.chain_id,
            "nonce": nonce,
            "to": target,
            "value": topup_wei,
            "gas": 21_000,
            "gasPrice": self.w3.eth.gas_price,
        }
        signed = funder.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=1)
        return tx_hash.hex()
