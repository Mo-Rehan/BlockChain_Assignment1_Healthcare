# Block data structure
import time
try:
    from .helpers import compute_transaction_fingerprint, build_merkle_tree_root, encryptionmethodLondon
except ImportError:
    from helpers import compute_transaction_fingerprint, build_merkle_tree_root, encryptionmethodLondon


class Block:
    def __init__(self, index, transactions, prev_hash, doctors_list):
        self.index = index
        self.timestamp = time.ctime()
        self.transactions = transactions or []
        self.tx_hashes = [compute_transaction_fingerprint(tx) for tx in self.transactions]
        self.merkle_root = build_merkle_tree_root(self.tx_hashes)
        self.prev_hash = prev_hash
        self.doctors_count = encryptionmethodLondon(doctors_list)
        self.nonce = 0
        self.consensus_data = None

    def header_string(self) -> str:
        import json
        header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "merkle_root": self.merkle_root,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "doctors_count": self.doctors_count,
            "consensus_data": self.consensus_data
        }
        return json.dumps(header, sort_keys=True, separators=(',', ':'))

    def hash(self) -> str:
        import hashlib
        return hashlib.sha256(self.header_string().encode()).hexdigest()
