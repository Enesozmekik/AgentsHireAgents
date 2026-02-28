from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import TransactionNotFound


@dataclass(frozen=True)
class TxResult:
    tx_hash: str
    status: int
    block_number: int
    gas_used: int


class MonadBridge:
    """
    Contract wrapper for build -> sign -> send -> wait flow.
    Designed for high-frequency usage with local pending-nonce tracking.
    """

    def __init__(self, w3: Web3, contract: Contract, default_gas_limit: int = 500_000) -> None:
        self.w3 = w3
        self.contract = contract
        self.default_gas_limit = default_gas_limit
        self._nonce_cache: Dict[str, int] = {}

    @classmethod
    def from_deployment_file(
        cls,
        w3: Web3,
        deployment_file: str | Path,
        default_gas_limit: int = 500_000,
    ) -> "MonadBridge":
        path = Path(deployment_file)
        if not path.exists():
            raise FileNotFoundError(f"Deployment file not found: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        address = payload["address"]
        abi = payload["abi"]
        contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)
        return cls(w3=w3, contract=contract, default_gas_limit=default_gas_limit)

    def read(self, fn_name: str, *args: Any) -> Any:
        fn = getattr(self.contract.functions, fn_name)(*args)
        return fn.call()

    def send_contract_tx(
        self,
        account: LocalAccount,
        fn_name: str,
        *args: Any,
        value_wei: int = 0,
        gas_limit: Optional[int] = None,
        max_fee_per_gas_wei: Optional[int] = None,
        max_priority_fee_per_gas_wei: Optional[int] = None,
        wait_timeout_sec: int = 120,
        wait_poll_sec: float = 1.0,
    ) -> TxResult:
        fn = getattr(self.contract.functions, fn_name)(*args)
        nonce = self._next_nonce(account.address)
        if gas_limit is None:
            try:
                estimated = fn.estimate_gas({"from": account.address, "value": value_wei})
                gas_limit = int(estimated * 1.2)
            except Exception:
                gas_limit = self.default_gas_limit

        tx: Dict[str, Any] = {
            "from": account.address,
            "nonce": nonce,
            "value": value_wei,
            "gas": gas_limit,
            "chainId": self.w3.eth.chain_id,
        }

        use_legacy = os.getenv("MONAD_USE_LEGACY_GAS", "1").strip().lower() in {"1", "true", "yes"}
        if use_legacy:
            tx["gasPrice"] = self.w3.eth.gas_price
        else:
            latest_block = self.w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas")
            if max_fee_per_gas_wei is not None and max_priority_fee_per_gas_wei is not None:
                tx["maxFeePerGas"] = max_fee_per_gas_wei
                tx["maxPriorityFeePerGas"] = max_priority_fee_per_gas_wei
            elif base_fee is not None:
                priority = self.w3.to_wei(2, "gwei")
                tx["maxPriorityFeePerGas"] = priority
                tx["maxFeePerGas"] = int(base_fee * 2 + priority)
            else:
                tx["gasPrice"] = self.w3.eth.gas_price

        built_tx = fn.build_transaction(tx)
        signed = account.sign_transaction(built_tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        receipt = self._wait_for_receipt(
            tx_hash=tx_hash,
            timeout_sec=wait_timeout_sec,
            poll_sec=wait_poll_sec,
        )
        return TxResult(
            tx_hash=tx_hash.hex(),
            status=int(receipt.status),
            block_number=int(receipt.blockNumber),
            gas_used=int(receipt.gasUsed),
        )

    def _next_nonce(self, address: str) -> int:
        chain_nonce = self.w3.eth.get_transaction_count(address, block_identifier="pending")
        cached = self._nonce_cache.get(address)
        if cached is None:
            next_nonce = chain_nonce
        else:
            next_nonce = max(chain_nonce, cached + 1)
        self._nonce_cache[address] = next_nonce
        return next_nonce

    def _wait_for_receipt(self, tx_hash: bytes, timeout_sec: int, poll_sec: float) -> Any:
        start = time.time()
        while True:
            try:
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return receipt
            except TransactionNotFound:
                pass
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"Receipt timeout for tx: {tx_hash.hex()}")
            time.sleep(poll_sec)
