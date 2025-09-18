# Validation functions for the healthcare blockchain system
import re
import hashlib
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .blockchain import Blockchain, Block


def validate_transaction_data(tx: dict) -> Tuple[bool, str]:
    # Check for required fields
    required_fields = ["hospital_id", "doctor_id", "patient_id", "record_id", "record_type", "operation"]
    
    for field in required_fields:
        if field not in tx:
            return False, f"Missing required field: {field}"
        if not str(tx[field]).strip():
            return False, f"Empty value for required field: {field}"
    
    # Validate ID formats (alphanumeric with optional hyphens/underscores)
    id_pattern = r'^[a-zA-Z0-9_-]+$'
    id_fields = ["hospital_id", "doctor_id", "patient_id", "record_id"]
    
    for field in id_fields:
        if not re.match(id_pattern, tx[field]):
            return False, f"Invalid format for {field}. Use alphanumeric characters, hyphens, or underscores only."
        if len(tx[field]) > 50:
            return False, f"{field} too long. Maximum 50 characters."
        if len(tx[field]) < 3:
            return False, f"{field} too short. Minimum 3 characters."
    
    # Validate record type
    valid_record_types = ["Diagnosis", "Prescription", "Test", "Emergency", "Consultation", "Surgery", "Lab_Result"]
    if tx["record_type"] not in valid_record_types:
        return False, f"Invalid record type. Must be one of: {', '.join(valid_record_types)}"
    
    # Validate operation
    valid_operations = ["Add", "Update", "Share", "Emergency_Add", "Delete"]
    if tx["operation"] not in valid_operations:
        return False, f"Invalid operation. Must be one of: {', '.join(valid_operations)}"
    
    # Validate amount if present
    if tx.get("amount"):
        try:
            amount = float(tx["amount"])
            if amount < 0:
                return False, "Amount cannot be negative"
            if amount > 1000000:  # Reasonable upper limit
                return False, "Amount too large. Maximum 1,000,000"
        except ValueError:
            return False, "Amount must be a valid number"
    
    # Validate prescription/details length
    if tx.get("prescription") and len(tx["prescription"]) > 1000:
        return False, "Prescription/details too long. Maximum 1000 characters."
    
    # Validate insurance ID format if present
    if tx.get("insurance_id") and tx["insurance_id"].strip():
        if not re.match(id_pattern, tx["insurance_id"]):
            return False, "Invalid insurance ID format"
        if len(tx["insurance_id"]) > 30:
            return False, "Insurance ID too long. Maximum 30 characters."
    
    # Check for SQL injection patterns (basic protection)
    dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_", "DROP", "DELETE", "INSERT", "UPDATE"]
    for field, value in tx.items():
        if isinstance(value, str):
            for pattern in dangerous_patterns:
                if pattern.lower() in value.lower():
                    return False, f"Potentially dangerous content detected in {field}"
    
    return True, "Valid transaction"


def validate_user_data(user_data: dict, role: str) -> Tuple[bool, str]:
    # Check required fields
    if "id" not in user_data or "name" not in user_data:
        return False, "Missing required fields: id and name"
    
    # Validate ID format
    user_id = user_data["id"].strip()
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        return False, "Invalid ID format. Use alphanumeric characters, hyphens, or underscores only."
    
    if len(user_id) < 3 or len(user_id) > 30:
        return False, "ID must be between 3 and 30 characters."
    
    # Validate name
    name = user_data["name"].strip()
    if not re.match(r'^[a-zA-Z\s\.-]+$', name):
        return False, "Invalid name format. Use letters, spaces, dots, and hyphens only."
    
    if len(name) < 2 or len(name) > 100:
        return False, "Name must be between 2 and 100 characters."
    
    # Role-specific validations
    if role not in ["doctor", "patient", "admin"]:
        return False, "Invalid role. Must be doctor, patient, or admin."
    
    # For patients, validate consent list if present
    if role == "patient" and "consent" in user_data:
        consent = user_data["consent"]
        if not isinstance(consent, list):
            return False, "Consent must be a list"
        
        for doctor_id in consent:
            if not isinstance(doctor_id, str) or not doctor_id.strip():
                return False, "Invalid doctor ID in consent list"
    
    return True, "Valid user data"


def validate_consensus_integrity(bc: 'Blockchain') -> Tuple[bool, str]:
    if not bc.consensus_mode:
        return True, "No consensus mode configured"

    if bc.consensus_mode != "DPoS":
        return False, "Only DPoS is supported in this implementation"

    if not bc.delegates:
        return False, "DPoS configured but no delegates found"

    # Validate delegates
    for delegate_id in bc.delegates:
        if not isinstance(delegate_id, str) or not delegate_id.strip():
            return False, f"Invalid delegate ID: {delegate_id}"
        if not bc.find_user(delegate_id):
            return False, f"Delegate {delegate_id} is not a registered user"
        # Patients cannot be delegates
        is_patient = any(p.get("id") == delegate_id for p in bc.users.get("patients", []))
        if is_patient:
            return False, f"Delegate {delegate_id} is a patient, which is not allowed"

    return True, "Consensus integrity validated"


def validate_chain_integrity(bc: 'Blockchain') -> Tuple[bool, str]:
    if not bc.chain:
        return True, "Empty chain"
    
    # Validate genesis block
    genesis = bc.chain[0]
    if genesis.index != 0:
        return False, "Genesis block must have index 0"
    
    if genesis.prev_hash != "0" * 64:
        return False, "Genesis block must have null previous hash"
    
    # Validate chain continuity
    for i in range(1, len(bc.chain)):
        current_block = bc.chain[i]
        prev_block = bc.chain[i-1]
        
        # Check index continuity
        if current_block.index != prev_block.index + 1:
            return False, f"Block index discontinuity at block {current_block.index}"
        
        # Check hash linkage
        if current_block.prev_hash != prev_block.hash():
            return False, f"Hash linkage broken at block {current_block.index}"
        
        # Validate block hash
        computed_hash = current_block.hash()
        if not computed_hash:
            return False, f"Invalid hash computation for block {current_block.index}"
        
        # Validate merkle root
        try:
            from .helpers import compute_transaction_fingerprint, build_merkle_tree_root
        except ImportError:
            from helpers import compute_transaction_fingerprint, build_merkle_tree_root
        tx_hashes = [compute_transaction_fingerprint(tx) for tx in current_block.transactions]
        computed_merkle = build_merkle_tree_root(tx_hashes)
        if current_block.merkle_root != computed_merkle:
            return False, f"Merkle root mismatch in block {current_block.index}"
        
        # Validate consensus data
        if not current_block.consensus_data:
            return False, f"Missing consensus data in block {current_block.index}"
        
        if "mode" not in current_block.consensus_data:
            return False, f"Missing consensus mode in block {current_block.index}"
    
    return True, "Chain integrity validated"


def validate_access_permissions(bc: 'Blockchain', doctor_id: str, patient_id: str) -> Tuple[bool, str]:
    # Find doctor
    doctor = next((d for d in bc.users["doctors"] if d["id"] == doctor_id), None)
    if not doctor:
        return False, "Doctor not found"
    
    # Find patient
    patient = next((p for p in bc.users["patients"] if p["id"] == patient_id), None)
    if not patient:
        return False, "Patient not found"
    
    # Check consent
    if doctor_id not in patient.get("consent", []):
        return False, "No consent given by patient"
    
    return True, "Access permitted"


def sanitize_input(input_str: str) -> str:
    if not isinstance(input_str, str):
        return str(input_str)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', input_str)
    
    # Limit length
    sanitized = sanitized[:1000]
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    return sanitized
