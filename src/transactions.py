# Medical Record Transaction Processing
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .blockchain import Blockchain

# Use centralized validation to keep rules consistent across CLI, GUI, and block verification
try:
    from .validation import validate_transaction_data as validate_tx
except ImportError:
    from validation import validate_transaction_data as validate_tx


def input_transaction(bc: 'Blockchain') -> Optional[dict]:
    print("\nEnter transaction details:")

    # Enhanced input collection with validation
    doctor_id = input("Attending Physician ID: ").strip()
    patient_id = input("Patient Identifier: ").strip()

    # Basic validation for required fields
    if not doctor_id or not patient_id:
        print("Doctor ID and Patient ID are required.")
        return None

    tx = {
        "hospital_id": input("Hospital ID: ").strip(),
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "insurance_id": input("Insurance Provider ID: ").strip(),
        "record_id": input("Medical Record ID: ").strip(),
        "record_type": input("Record Type (Diagnosis/Prescription/Test/Consultation/Surgery/Lab_Result/Emergency): ").strip(),
        "operation": input("Operation Type (Add/Update/Share): ").strip(),
        "prescription": input("Prescription/Medical Details: ").strip(),
        "amount": input("Associated Amount: ").strip(),
        "timestamp": time.ctime()
    }

    # Validate patient exists
    patient = next((p for p in bc.users["patients"] if p["id"] == tx["patient_id"]), None)
    if not patient:
        print("Patient not found. Transaction aborted.")
        bc.log_access(tx["doctor_id"], "WRITE", tx["record_id"], False, reason="patient_not_found")
        return None

    # Validate doctor has consent
    if tx["doctor_id"] not in patient["consent"]:
        print("Transaction rejected. Patient consent not found for this doctor.")
        bc.log_access(tx["doctor_id"], "WRITE", tx["record_id"], False, reason="no_consent")
        return None

    # Validate doctor exists
    doctor = next((d for d in bc.users["doctors"] if d["id"] == tx["doctor_id"]), None)
    if not doctor:
        print("Doctor not found. Transaction aborted.")
        bc.log_access(tx["doctor_id"], "WRITE", tx["record_id"], False, reason="doctor_not_found")
        return None

    # Validate transaction structure and fields
    ok, msg = validate_tx(tx)
    if not ok:
        print(f"Invalid transaction: {msg}")
        bc.log_access(tx["doctor_id"], "WRITE", tx["record_id"], False, reason="invalid_tx")
        return None

    bc.log_access(tx["doctor_id"], "WRITE", tx["record_id"], True)
    return tx


def create_emergency_transaction(bc: 'Blockchain') -> Optional[dict]:
    print("\nEMERGENCY TRANSACTION - Bypasses consent checks")
    emergency_code = input("Enter emergency authorization code: ").strip()
    
    # Simple emergency code validation (in real system, this would be more secure)
    if emergency_code != "EMERGENCY_2024":
        print("Invalid emergency code. Transaction aborted.")
        return None
    
    tx = {
        "hospital_id": input("Hospital ID: ").strip(),
        "doctor_id": input("Doctor ID: ").strip(),
        "patient_id": input("Patient ID: ").strip(),
        "insurance_id": input("Insurance ID: ").strip(),
        "record_id": input("Record ID: ").strip(),
        "record_type": "Emergency",
        "operation": "Emergency_Add",
        "prescription": input("Emergency Treatment Details: ").strip(),
        "amount": input("Amount: ").strip(),
        "timestamp": time.ctime(),
        "emergency": True,
        "emergency_code": emergency_code
    }

    # Validate patient exists
    patient = next((p for p in bc.users["patients"] if p["id"] == tx["patient_id"]), None)
    if not patient:
        print("Patient not found. Emergency transaction aborted.")
        bc.log_access(tx["doctor_id"], "EMERGENCY_WRITE", tx["record_id"], False, reason="patient_not_found")
        return None

    # Validate doctor exists
    doctor = next((d for d in bc.users["doctors"] if d["id"] == tx["doctor_id"]), None)
    if not doctor:
        print("Doctor not found. Emergency transaction aborted.")
        bc.log_access(tx["doctor_id"], "EMERGENCY_WRITE", tx["record_id"], False, reason="doctor_not_found")
        return None

    # Validate transaction structure and fields (even in emergency)
    ok, msg = validate_tx(tx)
    if not ok:
        print(f"Invalid emergency transaction: {msg}")
        return None

    bc.log_access(tx["doctor_id"], "EMERGENCY_WRITE", tx["record_id"], True, reason="emergency_override")
    print("Emergency transaction created.")
    return tx


def validate_transaction_data(tx: dict) -> tuple[bool, str]:
    # Proxy to centralized validator to avoid divergence of rules
    return validate_tx(tx)
