# Healthcare Blockchain Implementation
# Student implementation for medical record management

import hashlib
import json
import random
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
        # Stakes for users (doctor/patient). Map user_id -> numeric stake
        self.stakes: dict[str, float] = {}
        # Configurable maximum allowed stake per user (None or number)
        self.stake_cap: float | None = None
        # Patient voting: map patient_id -> doctor_id (their current vote)
        self.votes: dict[str, str] = {}
        # Round-robin producer pointer for DPoS
        self.producer_pointer: int = 0
        # Winners-only round-robin pointer (among tied top vote winners)
        self.winners_pointer: int = 0
        # Economic parameters
        self.block_reward: float = 100.0  # total reward per produced block
        self.share_ratio: float = 0.30    # fraction shared to supporters
        # Account balances (for doctors/patients/admins)
        self.balances: dict[str, float] = {}

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
        # Log genesis block creation with metadata
        try:
            self.log_access(
                user_id="system",
                action="BLOCK_ADDED",
                record_id="genesis",
                success=True,
                index=block.index,
                hash=block.hash(),
                prev_hash=block.prev_hash,
                merkle_root=block.merkle_root,
                consensus_data=block.consensus_data,
                tx_count=len(block.transactions),
            )
        except Exception:
            pass

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
        consensus_meta = {"mode": mode}
        producer = None
        if mode == "DPoS":
            # Winners-only scheduling: compute tied top winners from votes (patients' stake weights)
            winners = self.get_winners_set()
            if winners:
                # Round-robin among winners only
                if self.winners_pointer >= len(winners) or self.winners_pointer < 0:
                    self.winners_pointer = 0
                pointer_before = self.winners_pointer
                producer = winners[self.winners_pointer]
                self.winners_pointer = (self.winners_pointer + 1) % len(winners)
                consensus_meta["winners"] = winners
                consensus_meta["winner_pointer_before"] = pointer_before
                consensus_meta["winner_pointer_after"] = self.winners_pointer
            else:
                print("No winners from votes. Cannot produce block under winners-only scheduling.")
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
        block.consensus_data = {"producer": producer, "mode": mode, **consensus_meta}
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
        # Log block added with full metadata
        try:
            self.log_access(
                user_id=producer or "system",
                action="BLOCK_ADDED",
                record_id=str(block.index),
                success=True,
                index=block.index,
                hash=block.hash(),
                prev_hash=block.prev_hash,
                merkle_root=block.merkle_root,
                consensus_mode=mode,
                consensus_data=consensus_meta,
                tx_count=len(block.transactions),
                transactions=block.transactions,
            )
        except Exception:
            pass

        # Distribute block rewards: producer keeps (1-share_ratio), supporters (patients who voted for producer) share 'share_ratio' by stake
        try:
            total_reward = float(self.block_reward)
            share_ratio = float(self.share_ratio)
            prod_share = total_reward * (1.0 - share_ratio)
            supporters_share = total_reward * share_ratio
            # credit producer
            if producer:
                self.balances[producer] = float(self.balances.get(producer, 0.0)) + prod_share
            # supporters: voters who voted for producer and are patients
            supporters = [pid for pid, did in (self.votes or {}).items() if did == producer and self.is_patient(pid)]
            weights = {pid: float(self.get_stake(pid)) for pid in supporters}
            total_weight = sum(weights.values())
            breakdown = {}
            if total_weight > 0 and supporters_share > 0:
                for pid, w in weights.items():
                    amt = supporters_share * (w / total_weight)
                    if amt <= 0:
                        continue
                    self.balances[pid] = float(self.balances.get(pid, 0.0)) + amt
                    breakdown[pid] = round(amt, 6)
            else:
                # no supporters with stake: give all to producer
                if producer:
                    self.balances[producer] = float(self.balances.get(producer, 0.0)) + supporters_share
            # Log reward distribution
            try:
                self.log_access(
                    user_id=producer or "system",
                    action="REWARD_DISTRIBUTED",
                    record_id=str(block.index),
                    success=True,
                    producer=producer,
                    total_reward=total_reward,
                    producer_share=round(prod_share, 6),
                    supporters_share=round(supporters_share, 6),
                    supporters_count=len(supporters),
                    breakdown=breakdown,
                )
            except Exception:
                pass
        except Exception as e:
            print("Reward distribution failed:", e)

        return block

    def log_access(self, user_id, action, record_id, success, reason=None, **metadata):
        entry = {
            "timestamp": time.ctime(),
            "user_id": user_id,
            "action": action,
            "record_id": record_id,
            "success": success,
            "reason": reason,
        }
        # Merge extra metadata fields into the log entry
        for k, v in (metadata or {}).items():
            # avoid overwriting core keys unless explicitly intended
            if k not in entry or k in ("reason",):
                entry[k] = v
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
            "delegates": self.delegates,
            "stakes": self.stakes,
            "stake_cap": self.stake_cap,
            "votes": self.votes,
            "producer_pointer": self.producer_pointer,
            "winners_pointer": self.winners_pointer,
            "block_reward": self.block_reward,
            "share_ratio": self.share_ratio,
            "balances": self.balances,
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
        # Load stakes (cap is deprecated/ignored)
        self.stakes = data.get("stakes", {})
        self.stake_cap = None
        # Load votes
        self.votes = data.get("votes", {})
        # Load round-robin pointer (guard against OOB)
        self.producer_pointer = int(data.get("producer_pointer", 0) or 0)
        # Load winners pointer
        self.winners_pointer = int(data.get("winners_pointer", 0) or 0)
        # Load economic params and balances
        self.block_reward = float(data.get("block_reward", 100.0))
        self.share_ratio = float(data.get("share_ratio", 0.30))
        self.balances = data.get("balances", {})

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

    # --- Stakes helpers ---
    def set_stake(self, user_id: str, amount: float) -> tuple[bool, str]:
        try:
            amt = float(amount)
        except Exception:
            return False, "Stake must be a number"
        if amt < 0:
            return False, "Stake cannot be negative"
        # Cap removed: no upper-bound enforcement
        if not self.find_user(user_id):
            return False, "User not found"
        self.stakes[user_id] = amt
        return True, "Stake set"

    def get_stake(self, user_id: str) -> float:
        try:
            return float(self.stakes.get(user_id, 0))
        except Exception:
            return 0.0

    def set_stake_cap(self, cap: float | None) -> tuple[bool, str]:
        # Feature removed: always disable cap and keep None
        self.stake_cap = None
        return True, "Stake cap feature removed; cap disabled"

    def enforce_stake_cap(self):
        """Stake cap feature removed. This is a no-op kept for backward compatibility."""
        return []

    # --- Voting (patients vote for doctor delegates, weighted by patient stake) ---
    def set_vote(self, voter_id: str, candidate_id: str) -> tuple[bool, str]:
        # Any registered user can vote
        if not self.find_user(voter_id):
            return False, "Voter not found"
        # Candidate must be a doctor (keeping producer role consistent)
        if not self.find_user(candidate_id) or not self.is_doctor(candidate_id):
            return False, "Doctor (candidate) not found"
        self.votes[voter_id] = candidate_id
        return True, "Vote recorded"

    def tally_votes(self) -> dict:
        """Return a dict: doctor_id -> { 'weight': sum_stake, 'count': num_votes }"""
        tally: dict[str, dict] = {}
        for pid, did in self.votes.items():
            if not self.is_doctor(did):
                continue
            # weight = patient stake
            w = self.get_stake(pid)
            if did not in tally:
                tally[did] = {"weight": 0.0, "count": 0}
            tally[did]["weight"] += float(w)
            tally[did]["count"] += 1
        return tally

    def select_delegates_from_votes(self, top_n: int, prefer_existing: bool = True) -> list[str]:
        """Select top-N doctor delegates based on patient-weighted votes.
        Tie-breaker: prefer existing delegates if prefer_existing, then by doctor_id ascending.
        Updates self.delegates and returns the new list.
        """
        tally = self.tally_votes()
        # Build list of (doctor_id, weight, count)
        candidates = [(did, meta.get("weight", 0.0), meta.get("count", 0)) for did, meta in tally.items() if self.is_doctor(did)]
        old = list(self.delegates)
        def sort_key(item):
            did, weight, cnt = item
            pref = 0
            if prefer_existing and did in old:
                pref = -1  # existing delegates get priority in ties
            return (-weight, pref, did)
        ranked = sorted(candidates, key=sort_key)
        new_delegates = [did for did, _, _ in ranked[: max(0, int(top_n))]]
        self.delegates = new_delegates
        return new_delegates

    def get_winners_set(self) -> list[str]:
        """Return the set of doctors that have the maximum vote weight.
        Sorted deterministically by doctor_id ascending for stable round-robin.
        """
        tally = self.tally_votes()
        if not tally:
            return []
        max_w = max(float(meta.get("weight", 0.0)) for meta in tally.values())
        winners = [did for did, meta in tally.items() if float(meta.get("weight", 0.0)) == max_w and self.is_doctor(did)]
        winners = sorted(set(winners))
        return winners

    def current_expected_producer(self) -> tuple[str | None, list[str]]:
        """Compute the current expected producer without advancing pointers.
        Returns (producer_id_or_None, winners_list)."""
        winners = self.get_winners_set()
        if not winners:
            return None, winners
        idx = self.winners_pointer
        if idx < 0 or idx >= len(winners):
            idx = 0
        return winners[idx], winners

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
