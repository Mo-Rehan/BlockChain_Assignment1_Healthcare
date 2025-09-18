import json
import time
import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(__file__))
st.set_page_config(page_title="Healthcare Blockchain", layout="wide")

try:
    from .blockchain import Blockchain
    from .validation import (
        validate_chain_integrity as ext_validate_chain,
        validate_consensus_integrity,
        validate_access_permissions,
        validate_transaction_data as ext_validate_tx,
    )
except ImportError:
    from blockchain import Blockchain
    from validation import (
        validate_chain_integrity as ext_validate_chain,
        validate_consensus_integrity,
        validate_access_permissions,
        validate_transaction_data as ext_validate_tx,
    )


def init_app_state():
    if "bc" not in st.session_state:
        bc = Blockchain()
        bc.load_state()
        st.session_state.bc = bc


def app_header():
    st.markdown(
        """
        <style>
        .app-header {background: linear-gradient(90deg,#4158D0 0%,#C850C0 46%,#FFCC70 100%); 
            color:white; padding:18px; border-radius:12px; margin-bottom:16px}
        .card {background:white; padding:16px; border-radius:10px; box-shadow:0 2px 8px rgba(0,0,0,.08);}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="app-header"><h2>Healthcare Blockchain</h2><p>DPoS • Verified Blocks • Merkle Root</p></div>', unsafe_allow_html=True)


def dashboard():
    bc = st.session_state.bc
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Blocks", len(bc.chain))
    with c2: st.metric("Doctors", len(bc.users["doctors"]))
    with c3: st.metric("Patients", len(bc.users["patients"]))
    with c4: st.metric("Admins", len(bc.users["admins"]))

    st.subheader("Recent Logs")
    logs = bc.access_logs[-5:]
    if not logs:
        st.info("No logs yet")
    else:
        for e in reversed(logs):
            st.write(f"{e['timestamp']} | {e['user_id']} | {e['action']} | {e['record_id']}" + (f" | {e['reason']}" if e.get('reason') else ""))

    st.subheader("Validation")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Validate Chain (external)"):
            ok, msg = ext_validate_chain(bc)
            st.success(msg) if ok else st.error(msg)
    with c2:
        if st.button("Validate Consensus"):
            ok, msg = validate_consensus_integrity(bc)
            st.success(msg) if ok else st.error(msg)


def users_page():
    bc = st.session_state.bc
    t1, t2 = st.tabs(["Register", "Consent"])

    with t1:
        role = st.selectbox("Role", ["doctor", "patient", "admin"], key="reg_role")
        uid = st.text_input("ID", key="reg_id")
        name = st.text_input("Name", key="reg_name")
        if st.button("Register User"):
            if not uid or not name:
                st.error("ID and Name required")
            elif bc.find_user(uid):
                st.error("User already exists")
            else:
                if role == "doctor":
                    bc.users["doctors"].append({"id": uid, "name": name})
                elif role == "patient":
                    bc.users["patients"].append({"id": uid, "name": name, "consent": []})
                else:
                    bc.users["admins"].append({"id": uid, "name": name})
                bc.save_state()
                st.success("User registered")

        st.markdown("---")
        st.write("Users:")
        for role in ("doctors", "patients", "admins"):
            st.write(f"- {role}: {[u['id'] for u in bc.users[role]]}")

    with t2:
        patients = [p["id"] for p in bc.users["patients"]]
        doctors = [d["id"] for d in bc.users["doctors"]]
        if not patients or not doctors:
            st.info("Add at least one patient and one doctor")
        else:
            pid = st.selectbox("Patient", patients, key="consent_pid")
            did = st.selectbox("Doctor", doctors, key="consent_did")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Give Consent"):
                    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
                    if did not in patient["consent"]:
                        patient["consent"].append(did)
                        bc.save_state(); st.success("Consent added")
                    else:
                        st.warning("Consent already exists")
            with c2:
                if st.button("Revoke Consent"):
                    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
                    if did in patient["consent"]:
                        patient["consent"].remove(did)
                        bc.save_state(); st.success("Consent revoked")
                    else:
                        st.info("Nothing to revoke")


def consensus_page():
    bc = st.session_state.bc
    st.write("Consensus Mode: " + (bc.consensus_mode or "Not set"))
    if st.button("Enable DPoS"):
        bc.consensus_mode = "DPoS"; bc.save_state(); st.success("DPoS enabled")

    delegate_id = st.text_input("Add Delegate (ID)")
    if st.button("Add Delegate"):
        if not delegate_id or not bc.find_user(delegate_id):
            st.error("Delegate must be a registered user")
        elif hasattr(bc, "is_patient") and bc.is_patient(delegate_id):
            st.error("Patients cannot be delegates")
        elif delegate_id in bc.delegates:
            st.warning("Already a delegate")
        else:
            bc.delegates.append(delegate_id)
            bc.save_state(); st.success("Delegate added")

    if bc.delegates:
        st.write("Delegates:", ", ".join(bc.delegates))
    if st.button("Reset DPoS"):
        bc.consensus_mode = None; bc.delegates.clear(); bc.save_state(); st.info("DPoS reset")


def records_page():
    bc = st.session_state.bc
    t1, t2 = st.tabs(["Add Record", "Emergency Record"])

    with t1:
        with st.form("tx_form"):
            c1, c2 = st.columns(2)
            with c1:
                hospital_id = st.text_input("Hospital ID")
                doctor_id = st.text_input("Doctor ID")
                patient_id = st.text_input("Patient ID")
                insurance_id = st.text_input("Insurance ID (optional)")
            with c2:
                record_id = st.text_input("Record ID")
                record_type = st.selectbox("Record Type", ["Diagnosis","Prescription","Test","Consultation","Surgery","Lab_Result"])
                operation = st.selectbox("Operation", ["Add","Update","Share"]) 
                amount = st.text_input("Amount (optional)")
            prescription = st.text_area("Details")
            submitted = st.form_submit_button("Add")
        if submitted:
            tx = {
                "hospital_id": hospital_id.strip(),
                "doctor_id": doctor_id.strip(),
                "patient_id": patient_id.strip(),
                "insurance_id": insurance_id.strip(),
                "record_id": record_id.strip(),
                "record_type": record_type,
                "operation": operation,
                "prescription": prescription.strip(),
                "amount": amount.strip(),
                "timestamp": time.ctime(),
            }
            ok, msg = ext_validate_tx(tx)
            if not ok:
                st.error(msg); return
            perm_ok, reason = validate_access_permissions(bc, doctor_id, patient_id)
            if not perm_ok:
                st.error(f"Access denied: {reason}"); bc.log_access(doctor_id, "WRITE", record_id, False, reason=reason); return
            blk = bc.add_block_with_consensus([tx])
            if blk: st.success(f"Added in block {blk.index}"); bc.save_state()
            else: st.error("Failed to add block (check consensus/delegates)")

    with t2:
        code = st.text_input("Emergency Code", type="password")
        with st.form("em_form"):
            c1, c2 = st.columns(2)
            with c1:
                eh = st.text_input("Hospital ID", key="eh")
                ed = st.text_input("Doctor ID", key="ed")
                ep = st.text_input("Patient ID", key="ep")
                ei = st.text_input("Insurance ID", key="ei")
            with c2:
                er = st.text_input("Record ID", key="er")
                ea = st.text_input("Amount", key="ea")
            et = st.text_area("Emergency Details", key="et")
            esub = st.form_submit_button("Add Emergency Record")
        if esub:
            if code != "EMERGENCY_2024":
                st.error("Invalid code"); return
            tx = {
                "hospital_id": eh.strip(),
                "doctor_id": ed.strip(),
                "patient_id": ep.strip(),
                "insurance_id": ei.strip(),
                "record_id": er.strip(),
                "record_type": "Emergency",
                "operation": "Emergency_Add",
                "prescription": et.strip(),
                "amount": ea.strip(),
                "timestamp": time.ctime(),
                "emergency": True,
                "emergency_code": code,
            }
            ok, msg = ext_validate_tx(tx)
            if not ok:
                st.error(msg); return
            blk = st.session_state.bc.add_block_with_consensus([tx])
            if blk:
                bc.log_access(ed, "EMERGENCY_WRITE", er, True, reason="emergency_override")
                st.success(f"Emergency record in block {blk.index}"); bc.save_state()
            else:
                st.error("Failed to add emergency record")


def explorer_page():
    bc = st.session_state.bc
    if not bc.chain:
        st.info("Create a genesis block first from the CLI or by adding a record")
        return
    idx = st.selectbox("Select Block", list(range(len(bc.chain))))
    blk = bc.chain[idx]
    c1, c2 = st.columns(2)
    with c1:
        st.write("Index:", blk.index)
        st.write("Timestamp:", blk.timestamp)
        st.write("Prev Hash:", blk.prev_hash)
        st.write("Merkle Root:", blk.merkle_root)
        st.write("Hash:", blk.hash())
        st.write("Nonce:", blk.nonce)
    with c2:
        st.write("Consensus:", json.dumps(blk.consensus_data, indent=2))
    st.write("Transactions:")
    for i, tx in enumerate(blk.transactions):
        with st.expander(f"Transaction {i+1}: {tx.get('record_id','?')}"):
            st.json(tx)


def admin_page():
    bc = st.session_state.bc
    if not bc.chain:
        if st.button("Create Genesis Block"):
            bc.create_genesis(); bc.save_state(); st.success("Genesis created")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Validate Chain (built-in)"):
            ok = bc.validate_chain()
            st.success("Chain valid") if ok else st.error("Chain invalid")
    with c2:
        if st.button("Fix Chain Links/Merkle"):
            bc.fix_chain_integrity()
    with c3:
        if st.button("Save State"):
            bc.save_state(); st.success("Saved")

    st.subheader("Access Logs")
    if not bc.access_logs:
        st.info("No logs")
    else:
        for log in reversed(bc.access_logs[-50:]):
            st.write(json.dumps(log))


def main():
    init_app_state()
    app_header()
    page = st.sidebar.selectbox(
        "Navigate",
        ["Dashboard", "Users", "Records", "Consensus", "Explorer", "Admin"],
    )
    if page == "Dashboard":
        dashboard()
    elif page == "Users":
        users_page()
    elif page == "Records":
        records_page()
    elif page == "Consensus":
        consensus_page()
    elif page == "Explorer":
        explorer_page()
    else:
        admin_page()


if __name__ == "__main__":
    main()
