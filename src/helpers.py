# Helper functions for healthcare blockchain
import hashlib
import json


def compute_transaction_fingerprint(healthcare_record):
    normalized_record = json.dumps(healthcare_record, sort_keys=True, separators=(',', ':'))
    hash_object = hashlib.sha256(normalized_record.encode('utf-8'))
    return hash_object.hexdigest()


def build_merkle_tree_root(medical_tx_fingerprints):
    if not medical_tx_fingerprints:
        return hashlib.sha256(b'').hexdigest()

    current_level = medical_tx_fingerprints.copy()

    while len(current_level) > 1:
        if len(current_level) % 2 == 1:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
            next_level.append(parent_hash)

        current_level = next_level

    return current_level[0]


def encryptionmethodLondon(doctors_list):
    return len(doctors_list)
