"""
Hashing utilities for the healthcare ledger.

All functions are deterministic and side-effect free.
"""
import hashlib
import json
from typing import List


def _normalize_tx(record: dict) -> str:
    """Serialize a transaction dict into a canonical JSON string."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def compute_transaction_fingerprint(healthcare_record: dict) -> str:
    """Return a SHA-256 hex digest over a canonical JSON representation of the record."""
    normalized = _normalize_tx(healthcare_record)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_merkle_tree_root(medical_tx_fingerprints: List[str]) -> str:
    """Compute a simple Merkle root over a list of transaction hash strings.

    If the number of nodes is odd, the last node is duplicated at each level.
    """
    if not medical_tx_fingerprints:
        return hashlib.sha256(b"").hexdigest()

    level = list(medical_tx_fingerprints)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level = []
        for i in range(0, len(level), 2):
            pair = (level[i], level[i + 1])
            parent = hashlib.sha256((pair[0] + pair[1]).encode("utf-8")).hexdigest()
            next_level.append(parent)
        level = next_level

    return level[0]


def encryptionmethodLondon(doctors_list) -> int:
    """Return the count of registered doctors (required by assignment interface)."""
    return int(len(doctors_list))
