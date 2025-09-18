# View and display functionality for the healthcare blockchain
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .blockchain import Blockchain


def show_chain(bc: 'Blockchain'):
    if not bc.chain:
        print("Chain empty. Create genesis block first.")
        return
        
    for blk in bc.chain:
        print(f"\n--- Block {blk.index} ---")
        print("Timestamp:", blk.timestamp)
        print("Prev Hash:", (blk.prev_hash[:16] + "...") if blk.prev_hash else "None")
        print("Merkle Root:", blk.merkle_root)
        print("Doctors Count:", blk.doctors_count)
        print("Nonce:", blk.nonce)
        print("Consensus Data:", json.dumps(blk.consensus_data, indent=2))
        print("Block Hash:", blk.hash())
        print("Transactions:")
        for t in blk.transactions:
            print(" -", t.get("record_id","?"), "|", t.get("operation","?"), "|", 
                  t.get("doctor_id","?"), "->", t.get("patient_id","?"))


def view_access_logs(bc: 'Blockchain'):
    if not bc.access_logs:
        print("No logs yet.")
        return
        
    print("\n--- Access Logs ---")
    for e in bc.access_logs:
        print(json.dumps(e, indent=2))


def view_record_history(bc: 'Blockchain'):
    rid = input("Enter Record ID: ").strip()
    found = []
    
    for blk in bc.chain:
        for tx in blk.transactions:
            if tx.get("record_id") == rid:
                found.append({"block": blk.index, "tx": tx})
                
    if not found:
        print("No record history found.")
        return
        
    print(f"History for Record {rid}:")
    for item in found:
        print(f" Block {item['block']} | {item['tx']['timestamp']} | {item['tx']['operation']} by {item['tx']['doctor_id']}")
        print("  Details:", item['tx'])


def view_patient_records(bc: 'Blockchain'):
    pid = input("Enter Patient ID: ").strip()
    
    # Verify patient exists
    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
    if not patient:
        print("Patient not found.")
        return
    
    found = []
    for blk in bc.chain:
        for tx in blk.transactions:
            if tx.get("patient_id") == pid:
                found.append({"block": blk.index, "tx": tx})
                
    if not found:
        print(f"No records found for patient {patient['name']} ({pid}).")
        return
        
    print(f"\nAll Records for Patient {patient['name']} ({pid}):")
    for item in found:
        tx = item['tx']
        print(f"\n Block {item['block']} | Record ID: {tx.get('record_id', 'N/A')}")
        print(f" Timestamp: {tx.get('timestamp', 'N/A')}")
        print(f" Doctor: {tx.get('doctor_id', 'N/A')}")
        print(f" Hospital: {tx.get('hospital_id', 'N/A')}")
        print(f" Type: {tx.get('record_type', 'N/A')}")
        print(f" Operation: {tx.get('operation', 'N/A')}")
        print(f" Details: {tx.get('prescription', 'N/A')}")
        if tx.get('amount'):
            print(f" Amount: {tx['amount']}")


def view_doctor_activity(bc: 'Blockchain'):
    did = input("Enter Doctor ID: ").strip()
    
    # Verify doctor exists
    doctor = next((d for d in bc.users["doctors"] if d["id"] == did), None)
    if not doctor:
        print("Doctor not found.")
        return
    
    # Count transactions
    transaction_count = 0
    patients_treated = set()
    record_types = {}
    
    for blk in bc.chain:
        for tx in blk.transactions:
            if tx.get("doctor_id") == did:
                transaction_count += 1
                patients_treated.add(tx.get("patient_id"))
                record_type = tx.get("record_type", "Unknown")
                record_types[record_type] = record_types.get(record_type, 0) + 1
    
    print(f"\nActivity Summary for Dr. {doctor['name']} ({did}):")
    print(f" Total Transactions: {transaction_count}")
    print(f" Patients Treated: {len(patients_treated)}")
    print(f" Record Types:")
    for rtype, count in record_types.items():
        print(f"   {rtype}: {count}")
    
    # Show consensus activity if applicable
    if hasattr(bc, 'activity') and did in getattr(bc, 'activity', {}):
        print(f" Consensus Activity Score: {bc.activity[did]}")
    if hasattr(bc, 'stakes') and did in getattr(bc, 'stakes', {}):
        print(f" Stake Amount: {bc.stakes[did]}")


def view_blockchain_stats(bc: 'Blockchain'):
    print("\n--- Blockchain Statistics ---")
    print(f"Total Blocks: {len(bc.chain)}")
    print(f"Total Doctors: {len(bc.users['doctors'])}")
    print(f"Total Patients: {len(bc.users['patients'])}")
    print(f"Total Admins: {len(bc.users['admins'])}")
    print(f"Total Access Logs: {len(bc.access_logs)}")
    print(f"Consensus Mode: {bc.consensus_mode or 'Not configured'}")
    
    # Count total transactions
    total_transactions = sum(len(block.transactions) for block in bc.chain)
    print(f"Total Transactions: {total_transactions}")
    
    # Count successful vs failed access attempts
    successful_access = sum(1 for log in bc.access_logs if log.get("success"))
    failed_access = len(bc.access_logs) - successful_access
    print(f"Successful Access Attempts: {successful_access}")
    print(f"Failed Access Attempts: {failed_access}")
    
    if bc.consensus_mode:
        print(f"\nConsensus Configuration:")
        if bc.consensus_mode in ["PoS", "PoI"]:
            print(f" Validators with Stakes: {len(bc.stakes)}")
        elif bc.consensus_mode == "DPoS":
            print(f" Delegates: {len(bc.delegates)}")
        elif bc.consensus_mode == "PoET":
            print(f" PoET Validators: {len(bc.poet_waits)}")
