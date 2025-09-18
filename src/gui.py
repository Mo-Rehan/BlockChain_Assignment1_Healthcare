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
    # Hardcoded theme values for dark mode
    accent, font, radius, scale, dark = "#00E676", "Share Tech Mono (Digital)", 10, 100, True
    google_font_map = {
        "Orbitron (Digital)": ("https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700&display=swap", "'Orbitron', sans-serif"),
        "Share Tech Mono (Digital)": ("https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap", "'Share Tech Mono', monospace"),
        "VT323 (Retro)": ("https://fonts.googleapis.com/css2?family=VT323&display=swap", "'VT323', monospace"),
        "Inter": ("https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap", "'Inter', sans-serif"),
        "Roboto": ("https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap", "'Roboto', sans-serif"),
        "Source Sans 3": ("https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap", "'Source Sans 3', sans-serif"),
        "System Default": ("", "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"),
    }
    google_font_url, font_family = google_font_map.get(font, ("", "system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"))
    imports = f"@import url('{google_font_url}');" if google_font_url else ""
    imports += "@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');"
    # Colors for modes
    header_bg = "linear-gradient(90deg, #071018, #0b1220)" if dark else "linear-gradient(90deg, #eafaf0, #e2fff4)"
    body_g1, body_g2 = ("#0f172a", "#111827") if dark else ("#f7f8fc", "#eef1f7")
    text_main = "#00e676" if dark else "#0b1220"
    card_bg = "#0b1220" if dark else "#ffffff"
    card_fg = "#d7ffe6" if dark else "#0b1220"
    card_border = "#0f1b2d" if dark else "#e8ecf3"
    btn_text = "#071018" if dark else "#ffffff"
    node_bg = "#071018" if dark else "#ffffff"

    # Compose CSS in two parts to avoid f-string brace conflicts
    style_vars = f"""
        <style>
        {imports}
        :root {{
          --accent: {accent};
          --radius: {radius}px;
          --font: {font_family};
          --scale: {scale}%;
          --header-bg: {header_bg};
          --body-g1: {body_g1};
          --body-g2: {body_g2};
          --text-main: {text_main};
          --card-bg: {card_bg};
          --card-fg: {card_fg};
          --card-border: {card_border};
          --btn-text: {btn_text};
          --node-bg: {node_bg};
        }}
    """
    static_css = """
        html, body, [class*="css"] { font-family: var(--font) !important; font-size: calc(16px * var(--scale)/100); }
        .app-header { background: var(--header-bg); border: 1px solid var(--card-border); color: var(--text-main); padding:18px; border-radius:12px; margin-bottom:16px; text-shadow: 0 0 6px rgba(0,230,118,.5); letter-spacing:.5px; }
        .card { background: var(--card-bg); color: var(--card-fg); padding:16px; border-radius:var(--radius); box-shadow:0 2px 8px rgba(0,0,0,.08); border:1px solid var(--card-border); }
        .block-card { background: var(--card-bg); color: var(--card-fg); padding:14px; border-radius:var(--radius); box-shadow:0 1px 6px rgba(0,0,0,.3); margin-bottom:10px; border:1px solid var(--card-border) }
        body { background: linear-gradient(180deg, var(--body-g1) 0%, var(--body-g2) 100%) !important; }
        .stApp { background: linear-gradient(180deg, var(--body-g1) 0%, var(--body-g2) 100%) !important; }
        /* Force dark background across app containers */
        [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, var(--body-g1) 0%, var(--body-g2) 100%) !important; }
        [data-testid="stHeader"], [data-testid="stToolbar"] { background: transparent !important; }
        [data-testid="stSidebar"] { background: var(--node-bg) !important; border-right: 1px solid var(--card-border); }
        .block-container { background: transparent !important; }
        /* Make general text readable on dark */
        .block-container, .stMarkdown, .stText, .stWrite, p, li, h1, h2, h3, h4, h5, h6 { color: var(--card-fg) !important; }
        [data-testid="stMarkdownContainer"] * { color: var(--card-fg) !important; }
        .stExpander, .stExpander p, .stExpander div, .stExpander span { color: var(--card-fg) !important; }
        /* Ensure explorer page text is visible */
        .stMarkdown p, .stMarkdown pre, .stMarkdown code, .stMarkdown div { color: var(--card-fg) !important; }
        .stMarkdown pre { background-color: var(--node-bg) !important; border: 1px solid var(--card-border) !important; }
        /* Force text color for all direct children in explorer */
        .stMarkdown > * { color: var(--card-fg) !important; }
        /* Specific fix for index and nonce values */
        .stMarkdown code { color: var(--text-main) !important; font-weight: bold; }
        /* Style download buttons to match other buttons */
        .stDownloadButton > button { background: var(--accent) !important; color: var(--btn-text) !important; border: none !important; border-radius: var(--radius) !important; padding: 0.5rem 1rem !important; font-weight: 600 !important; }
        .stDownloadButton > button:hover { opacity: 0.9 !important; }
        .stButton>button { background: var(--accent); color: var(--btn-text); border: none; border-radius: var(--radius); padding: .5rem 1rem; font-weight:600; }
        .stButton>button:hover { opacity: .95; box-shadow: 0 0 0 3px rgba(0,0,0,.05) inset; }
        /* Inputs and selects in dark */
        .stTextInput>div>div>input, .stTextArea textarea { border-radius: var(--radius) !important; background: var(--node-bg); color: var(--card-fg); border: 1px solid var(--card-border); }
        /* Labels and placeholders readable on dark */
        .stTextInput label, .stTextArea label, .stSelectbox label, label { color: var(--card-fg) !important; }
        .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: rgba(215,255,230,.6) !important; }
        .stSelectbox>div>div { border-radius: var(--radius) !important; background: var(--node-bg); color: var(--card-fg); border: 1px solid var(--card-border); }
        [data-baseweb="tabs"] { background: var(--card-bg); border-radius: var(--radius); border: 1px solid var(--card-border); }
        .stMetric>div>div { font-size: 0.95rem; }
        .stMetric>div>div>span { font-family: 'Share Tech Mono', monospace !important; letter-spacing: .06em; }
        .seven { font-family: 'Share Tech Mono', monospace; letter-spacing: .08em; text-shadow: 0 0 6px rgba(0,230,118,.4); }
        /* Digital chain visuals */
        .chain-wrap { display:flex; gap:20px; align-items:center; overflow-x:auto; padding: 10px 2px; }
        .chain-node { min-width: 260px; background: var(--node-bg); color: var(--text-main); border:1px solid var(--card-border); border-radius:var(--radius); padding:12px; box-shadow:0 2px 8px rgba(0,0,0,.5); }
        .chain-node h4 { margin: 0 0 8px 0; font-weight:700; letter-spacing:.12em; text-shadow: 0 0 5px rgba(0,230,118,.6); }
        .chain-node .kv { font-family: 'Share Tech Mono', monospace; font-size: .9rem; }
        .connector { height: 2px; width: 60px; background: linear-gradient(90deg, #0f1b2d, var(--accent)); box-shadow: 0 0 6px rgba(0,230,118,.6); border-radius: 2px; }
        </style>
    """
    st.markdown(style_vars + static_css, unsafe_allow_html=True)
    st.markdown('<div class="app-header"><h2 class="seven">HEALTHCARE BLOCKCHAIN</h2><p class="seven">DPoS • VERIFIED BLOCKS • MERKLE ROOT</p></div>', unsafe_allow_html=True)


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
        cols = st.columns(3)
        for i, role in enumerate(("doctors", "patients", "admins")):
            with cols[i]:
                entries = bc.users[role]
                if entries:
                    st.table([{k: v for k, v in u.items() if k != "consent"} for u in entries])
                else:
                    st.info(f"No {role} registered")

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
        to_remove = st.multiselect("Remove delegates", bc.delegates)
        if st.button("Remove Selected") and to_remove:
            bc.delegates = [d for d in bc.delegates if d not in to_remove]
            bc.save_state(); st.success("Removed selected delegates")
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
                doctor_ids = [d["id"] for d in bc.users["doctors"]]
                patient_ids = [p["id"] for p in bc.users["patients"]]
                doctor_id = st.selectbox("Doctor", doctor_ids) if doctor_ids else st.text_input("Doctor ID")
                patient_id = st.selectbox("Patient", patient_ids) if patient_ids else st.text_input("Patient ID")
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
    st.subheader("Filters")
    fc1, fc2, fc3 = st.columns([1,1,1])
    with fc1:
        filter_record = st.text_input("Filter by record_id")
    with fc2:
        filter_patient = st.text_input("Filter by patient_id")
    with fc3:
        apply_filters = st.checkbox("Apply filters", value=bool(filter_record or filter_patient))

    if apply_filters and (filter_record or filter_patient):
        count = 0
        for blk in bc.chain:
            for tx in blk.transactions:
                if filter_record and tx.get("record_id") != filter_record:
                    continue
                if filter_patient and tx.get("patient_id") != filter_patient:
                    continue
                count += 1
                with st.container():
                    st.markdown(f"<div class='block-card'><b>Block</b>: {blk.index} &nbsp; <b>Time</b>: {blk.timestamp} &nbsp; <b>Hash</b>: {blk.hash()}</div>", unsafe_allow_html=True)
                    st.json(tx)
        if count == 0:
            st.info("No matching transactions found")
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


def chain_page():
    bc = st.session_state.bc
    if not bc.chain:
        st.info("Create a genesis block first from Admin page or by adding a record")
        return

    show_full = st.checkbox("Show full hashes", value=False)

    def fmt(s: str) -> str:
        if show_full or not s:
            return s
        return (s[:10] + "…" + s[-6:]) if len(s) > 18 else s

    html = ["<div class='chain-wrap'>"]
    for i, blk in enumerate(bc.chain):
        try:
            bhash = blk.hash()
        except Exception:
            bhash = ""
        mode = "-"
        producer = "-"
        if isinstance(getattr(blk, "consensus_data", None), dict):
            mode = blk.consensus_data.get("mode", "-")
            producer = blk.consensus_data.get("producer", "-")

        node = f"""
        <div class='chain-node'>
            <h4>BLOCK {blk.index}</h4>
            <div class='kv'>time: {blk.timestamp}</div>
            <div class='kv'>prev: {fmt(blk.prev_hash)}</div>
            <div class='kv'>hash: {fmt(bhash)}</div>
            <div class='kv'>merkle: {fmt(blk.merkle_root)}</div>
            <div class='kv'>mode: {mode} | producer: {producer}</div>
            <div class='kv'>tx: {len(blk.transactions)}</div>
        </div>
        """
        html.append(node)
        if i < len(bc.chain) - 1:
            html.append("<div class='connector'></div>")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

    # Export chain view
    export = [
        {
            "index": blk.index,
            "timestamp": blk.timestamp,
            "prev_hash": blk.prev_hash,
            "hash": (blk.hash() if hasattr(blk, "hash") else ""),
            "merkle_root": blk.merkle_root,
            "consensus_data": blk.consensus_data,
            "tx_count": len(blk.transactions),
        }
        for blk in bc.chain
    ]
    st.download_button(
        "Download Chain (JSON)",
        data=json.dumps(export, indent=2).encode("utf-8"),
        file_name=f"healthcare_blockchain_{int(time.time())}.json",
        mime="application/json",
    )


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
        confirm = st.checkbox("Confirm fix before running")
        if st.button("Fix Chain Links/Merkle"):
            if confirm:
                bc.fix_chain_integrity()
            else:
                st.warning("Please confirm before fixing")
    with c3:
        if st.button("Save State"):
            bc.save_state(); st.success("Saved")

    st.subheader("Access Logs")
    if not bc.access_logs:
        st.info("No logs")
    else:
        logs = list(reversed(bc.access_logs[-200:]))
        for log in logs:
            st.write(json.dumps(log))
        # Export buttons
        json_bytes = json.dumps(logs, indent=2).encode("utf-8")
        st.download_button("Download Logs (JSON)", data=json_bytes, file_name="access_logs.json", mime="application/json")
        # Build CSV
        if logs:
            keys = sorted({k for entry in logs for k in entry.keys()})
            rows = [",".join(keys)]
            for entry in logs:
                row = []
                for k in keys:
                    v = entry.get(k, "")
                    v = str(v).replace(",", ";")
                    row.append(v)
                rows.append(",".join(row))
            csv_bytes = ("\n".join(rows)).encode("utf-8")
            st.download_button("Download Logs (CSV)", data=csv_bytes, file_name="access_logs.csv", mime="text/csv")


def main():
    init_app_state()
    app_header()
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Users", "Records", "Consensus", "Explorer", "Chain", "Admin"],
        index=0,
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
    elif page == "Chain":
        chain_page()
    else:
        admin_page()


if __name__ == "__main__":
    main()
