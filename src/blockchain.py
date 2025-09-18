# Healthcare Blockchain Implementation
# Student implementation for medical record management

import hashlib
import json
import time
import secrets
import os
try:
    from .helpers import compute_transaction_fingerprint, build_merkle_tree_root, encryptionmethodLondon
    from .validation import validate_transaction_data as _validate_tx
    from .block import Block
except ImportError:
    from helpers import compute_transaction_fingerprint, build_merkle_tree_root, encryptionmethodLondon
    from validation import validate_transaction_data as _validate_tx
    from block import Block


# Block class moved to src/block.py


class Blockchain:
    def __init__(self):
        self.chain = []
        self.users = {"doctors": [], "patients": [], "admins": []}
        self.access_logs = []

        # DPoS consensus variables
        self.consensus_mode = None
        self.delegates = []

    # --- Role helper utilities ---
    def is_patient(self, uid: str) -> bool:
        return any(u.get("id") == uid for u in self.users.get("patients", []))

    def is_doctor(self, uid: str) -> bool:
        return any(u.get("id") == uid for u in self.users.get("doctors", []))

    def is_admin(self, uid: str) -> bool:
        return any(u.get("id") == uid for u in self.users.get("admins", []))

    # --- Block verification ---
    def verify_block(self, block: 'Block') -> tuple[bool, str]:
        # Verify index continuity
        if block.index != len(self.chain):
            return False, f"Block index mismatch. Expected {len(self.chain)}, got {block.index}"

        # Verify previous hash linkage
        expected_prev = "0" * 64 if block.index == 0 else self.chain[-1].hash()
        if block.prev_hash != expected_prev:
            return False, "Previous hash does not match chain tip"

        # Verify Merkle root
        recomputed_merkle = build_merkle_tree_root([compute_transaction_fingerprint(tx) for tx in block.transactions])
        if block.merkle_root != recomputed_merkle:
            return False, "Merkle root mismatch"

        # Verify consensus metadata
        if not block.consensus_data or "mode" not in block.consensus_data:
            return False, "Missing consensus metadata"
        if block.consensus_data.get("mode") != self.consensus_mode:
            return False, "Consensus mode mismatch"

        # DPoS-specific checks
        if self.consensus_mode == "DPoS":
            producer = block.consensus_data.get("producer")
            if not producer:
                return False, "Missing DPoS producer"
            if producer not in self.delegates:
                return False, "Producer is not an active delegate"
            if self.is_patient(producer):
                return False, "Patients cannot be delegates or block producers"

        # Validate transactions
        # for tx in block.transactions or []:
        #     ok, msg = _validate_tx(tx)
        #     if not ok:
        #         return False, f"Invalid transaction in block: {msg}"

        return True, "Block verified"

    def create_genesis(self):
        if self.chain:
            print("Warning: Genesis already exists. Create genesis only once.")
            return
        block = Block(0, [], "0"*64, self.users["doctors"])
        block.consensus_data = {"type": "genesis"}
        self.chain.append(block)
        print("Genesis block created.")

    def add_block_with_consensus(self, transactions):
        if not self.chain:
            print("Create genesis first.")
            return None
        if not self.consensus_mode:
            print("Set consensus mode first in 'Configure Consensus' menu.")
            return None
        if not transactions:
            print("Creating empty block (no transactions).")

        # DPoS is the only supported consensus mechanism for this assignment
        mode = self.consensus_mode
        producer = None
        consensus_meta = {"mode": mode}

        if mode == "DPoS":
            if not self.delegates:
                print("No delegates registered for DPoS. Elect delegates first.")
                return None
            # Round-robin delegate selection for block production
            delegate_index = (len(self.chain)) % len(self.delegates)
            producer = self.delegates[delegate_index]
            consensus_meta.update({
                "producer": producer,
                "delegate_index": delegate_index,
                "delegate_list": self.delegates.copy()
            })
            # Enforce: patient cannot be a delegate/producer
            if self.is_patient(producer):
                print("Selected producer is a patient. Patients cannot be delegates or producers.")
                return None
        else:
            print("Only DPoS consensus is supported in this healthcare blockchain.")
            print("Please configure DPoS consensus first.")
            return None

        # Pre-append chain integrity check to prevent tampering
        if not self.validate_chain():
            print("Chain integrity invalid. Aborting block addition.")
            return None

        prev_hash = self.chain[-1].hash()
        block = Block(len(self.chain), transactions, prev_hash, self.users["doctors"])
        block.consensus_data = consensus_meta
        block.nonce = secrets.randbelow(1 << 30)

        # Verify block before appending
        ok, msg = self.verify_block(block)
        if not ok:
            print(f"Block verification failed: {msg}")
            return None

        # Append and post-validate to ensure no tampering during write
        self.chain.append(block)
        if not self.validate_chain():
            # rollback
            self.chain.pop()
            print("Post-append chain validation failed. Block rejected.")
            return None

        print(f"Block {block.index} added by producer: {producer} (mode: {mode})")
        return block

    def log_access(self, user_id, action, record_id, success, reason=None):
        entry = {
            "timestamp": time.ctime(),
            "user_id": user_id,
            "action": action,
            "record_id": record_id,
            "success": success,
            "reason": reason
        }
        self.access_logs.append(entry)

    def find_user(self, uid):
        for role in ("doctors", "patients", "admins"):
            for u in self.users.get(role, []):
                if u.get("id") == uid:
                    return u
        return None

    def list_users(self):
        print("\n--- Registered Users ---")
        for role in ("doctors", "patients", "admins"):
            print(f"\n{role.capitalize()}:")
            for u in self.users.get(role, []):
                if role == "patients":
                    consent = u.get("consent", [])
                    print(f" - {u['id']} : {u['name']} (consent to: {consent})")
                else:
                    print(f" - {u['id']} : {u['name']}")

    def save_state(self, filename: str = "data/blockchain.json"):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        data = {
            "chain": [
                {
                    "index": blk.index,
                    "timestamp": blk.timestamp,
                    "transactions": blk.transactions,
                    "prev_hash": blk.prev_hash,
                    "merkle_root": blk.merkle_root,
                    "nonce": blk.nonce,
                    "doctors_count": blk.doctors_count,
                    "consensus_data": blk.consensus_data
                } for blk in self.chain
            ],
            "users": self.users,
            "access_logs": self.access_logs,
            "consensus_mode": self.consensus_mode,
            "delegates": self.delegates
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print("Blockchain state saved to", filename)

    def load_state(self, filename: str = "data/blockchain.json"):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            print("No saved state found. Starting fresh.")
            return

        self.users = data.get("users", {"doctors": [], "patients": [], "admins": []})
        self.access_logs = data.get("access_logs", [])
        self.consensus_mode = data.get("consensus_mode")
        # Load delegates but filter out any patients (not allowed to be delegates)
        loaded_delegates = data.get("delegates", [])
        filtered = [d for d in loaded_delegates if not self.is_patient(d)]
        removed = set(loaded_delegates) - set(filtered)
        self.delegates = filtered
        if removed:
            print(f"Removed invalid patient delegates from state: {sorted(list(removed))}")

        # Rebuild chain; recompute tx_hashes/merkle and warn if mismatch with stored merkle root
        self.chain = []
        for blk in data.get("chain", []):
            block = Block(blk["index"], blk["transactions"], blk["prev_hash"], self.users["doctors"])
            # Restore timestamp/nonce/consensus_data (but recompute merkle for integrity)
            block.timestamp = blk.get("timestamp", block.timestamp)
            block.nonce = blk.get("nonce", block.nonce)
            block.consensus_data = blk.get("consensus_data", block.consensus_data)
            # recompute tx_hashes & merkle root and compare if persisted value differs
            block.tx_hashes = [compute_transaction_fingerprint(tx) for tx in block.transactions]
            computed_merkle = build_merkle_tree_root(block.tx_hashes)
            persisted_merkle = blk.get("merkle_root")
            if persisted_merkle and persisted_merkle != computed_merkle:
                print(f"Warning: Merkle root mismatch in block {block.index} (persisted != computed).")
            block.merkle_root = computed_merkle
            self.chain.append(block)
        print("Blockchain state loaded from", filename)

    def validate_chain(self) -> bool:
        if not self.chain:
            print("Empty chain is valid.")
            return True

        print("\n--- Validating Blockchain Integrity ---")

        for i, block in enumerate(self.chain):
            # Recompute Merkle root
            recomputed_merkle = build_merkle_tree_root([compute_transaction_fingerprint(tx) for tx in block.transactions])
            if block.merkle_root != recomputed_merkle:
                print(f"Block {block.index}: Merkle root mismatch")
                return False

            # Check prev_hash linkage (skip genesis)
            if i > 0:
                if block.prev_hash != self.chain[i-1].hash():
                    print(f"Block {block.index}: prev_hash mismatch")
                    return False

            # Recompute block hash for consistency
            recomputed_hash = block.hash()
            if not recomputed_hash:
                print(f"Block {block.index}: Hash computation failed")
                return False

        print("Blockchain is valid.")
        return True

    def fix_chain_integrity(self) -> bool:
        print("\n--- Fixing Blockchain Integrity ---")

        if not self.chain:
            print("No blockchain to fix.")
            return False

        fixed = False

        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            expected_prev_hash = previous_block.hash()

            if current_block.prev_hash != expected_prev_hash:
                print(f"Fixing block {current_block.index} hash linkage...")
                current_block.prev_hash = expected_prev_hash
                fixed = True

            # Also fix merkle root if needed
            recomputed_merkle = build_merkle_tree_root([compute_transaction_fingerprint(tx) for tx in current_block.transactions])
            if current_block.merkle_root != recomputed_merkle:
                print(f"Fixing block {current_block.index} merkle root...")
                current_block.merkle_root = recomputed_merkle
                fixed = True

        if fixed:
            print("Blockchain integrity fixed.")
            self.save_state()
        else:
            print("Blockchain was already valid.")

        return True
