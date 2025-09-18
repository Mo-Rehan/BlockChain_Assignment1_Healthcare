# User management for healthcare blockchain
try:
    from .blockchain import Blockchain
except ImportError:
    pass


def register_user(bc):
    role = input("Enter role (doctor/patient/admin): ").strip().lower()
    uid = input("Enter ID: ").strip()
    name = input("Enter Name: ").strip()

    if not uid or not name:
        print("Error: ID and Name are required.")
        return

    if len(uid) < 2:
        print("Error: ID must be at least 2 characters.")
        return

    if bc.find_user(uid):
        print("Error: ID already exists.")
        return

    if role == "doctor":
        bc.users["doctors"].append({"id": uid, "name": name})
        print(f"Doctor {name} ({uid}) registered successfully.")
    elif role == "patient":
        bc.users["patients"].append({"id": uid, "name": name, "consent": []})
        print(f"Patient {name} ({uid}) registered successfully.")
    elif role == "admin":
        bc.users["admins"].append({"id": uid, "name": name})
        print(f"Admin {name} ({uid}) registered successfully.")
    else:
        print("Invalid role. Please use doctor/patient/admin.")


def give_consent(bc):
    pid = input("Patient ID: ").strip()
    did = input("Doctor ID to grant consent: ").strip()

    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
    doctor = next((d for d in bc.users["doctors"] if d["id"] == did), None)

    if not patient:
        print("Patient not found.")
        return

    if not doctor:
        print("Doctor not found.")
        return

    if did in patient["consent"]:
        print("Consent already exists.")
        return

    patient["consent"].append(did)
    print(f"Patient {patient['name']} granted consent to Dr {doctor['name']}")


def revoke_consent(bc: 'Blockchain'):
    pid = input("Patient ID: ").strip()
    did = input("Doctor ID to revoke consent: ").strip()
    
    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
    
    if not patient:
        print("Patient not found.")
        return
        
    if did not in patient["consent"]:
        print("No consent exists for this doctor.")
        return
        
    patient["consent"].remove(did)
    print(f"Consent revoked from doctor {did}")


def list_patient_consents(bc: 'Blockchain'):
    pid = input("Patient ID: ").strip()
    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
    
    if not patient:
        print("Patient not found.")
        return
        
    consents = patient.get("consent", [])
    if not consents:
        print(f"Patient {patient['name']} has not given consent to any doctors.")
        return
        
    print(f"\nConsents for Patient {patient['name']} ({pid}):")
    for doctor_id in consents:
        doctor = next((d for d in bc.users["doctors"] if d["id"] == doctor_id), None)
        doctor_name = doctor["name"] if doctor else "Unknown"
        print(f" - {doctor_id}: {doctor_name}")
