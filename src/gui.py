import json
import time
import textwrap
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
    # Load external CSS from assets/styles.css
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            external_css = f.read()
    except Exception as e:
        external_css = ""  # Fallback: no external CSS found
    # Inject variables + external stylesheet and close style tag
    st.markdown(style_vars + external_css + "</style>", unsafe_allow_html=True)
    st.markdown('<div class="app-header"><h2 class="seven">HEALTHCARE BLOCKCHAIN</h2><p class="seven">DPoS • VERIFIED BLOCKS • MERKLE ROOT</p></div>', unsafe_allow_html=True)


def dashboard():
    bc = st.session_state.bc
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Blocks", len(bc.chain))
    with c2: st.metric("Doctors", len(bc.users["doctors"]))
    with c3: st.metric("Patients", len(bc.users["patients"]))
    with c4: st.metric("Admins", len(bc.users["admins"]))

    st.subheader("Chain Overview")
    if not bc.chain:
        st.info("Create a genesis block first from Admin page or by adding a record")
    else:
        # Compact chain visual similar to chain_page
        show_full = False
        def fmt(s: str) -> str:
            if show_full or not s:
                return s
            return (s[:10] + "…" + s[-6:]) if isinstance(s, str) and len(s) > 18 else s

        html = ["<div class='chain-wrap'>"]
        for i, blk in enumerate(bc.chain):
            try:
                bhash = blk.hash()
            except Exception:
                bhash = ""
            mode = "-"; producer = "-"
            if isinstance(getattr(blk, "consensus_data", None), dict):
                mode = blk.consensus_data.get("mode", "-")
                producer = blk.consensus_data.get("producer", "-")
            # Producer stake (if any)
            p_stake = bc.get_stake(producer) if producer and producer != "-" else 0
            # Derive action and reason from transactions
            action = "No transactions"
            reason = "-"
            txs = blk.transactions or []
            if txs:
                if len(txs) == 1:
                    t = txs[0]
                    op = t.get("operation", "?")
                    rid = t.get("record_id", "?")
                    action = f"{op} {rid}"
                    reason_map = {
                        "Add": "New record added",
                        "Update": "Record updated",
                        "Share": "Record shared",
                        "Emergency_Add": "Emergency record added",
                        "Delete": "Record deleted",
                    }
                    reason = reason_map.get(op, "Transaction included")
                else:
                    unique_ops = sorted({t.get("operation", "?") for t in txs})
                    action = f"{len(txs)} transactions"
                    reason = ", ".join(unique_ops)
            # Compute consent pairs (patient -> doctor) for this block (Dashboard view)
            consent_pairs_pd = []
            if txs:
                seen = set()
                for t in txs:
                    did = t.get("doctor_id"); pid = t.get("patient_id")
                    if not did or not pid:
                        continue
                    key = (pid, did)
                    if key in seen:
                        continue
                    seen.add(key)
                    patient = next((p for p in bc.users.get("patients", []) if p.get("id") == pid), None)
                    if patient and did in patient.get("consent", []):
                        consent_pairs_pd.append(f"{pid}→{did}")
            node = textwrap.dedent(f"""
            <div class='chain-node'>
                <h4>BLOCK {blk.index}</h4>
                <div class='kv'>time: {blk.timestamp}</div>
                <div class='kv'>prev: {fmt(blk.prev_hash)}</div>
                <div class='kv'>hash: {fmt(bhash)}</div>
                <div class='kv'>merkle: {fmt(blk.merkle_root)}</div>
                <div class='kv'>mode: {mode} | delegate: {producer} (stake={p_stake})</div>
                <div class='kv'>action: {action}</div>
                <div class='kv'>reason: {reason}</div>
                {f"<div class='kv'>consent pairs: {', '.join(consent_pairs_pd)}</div>" if consent_pairs_pd else ""}
            </div>
            """)
            html.append(node)
            if i < len(bc.chain) - 1:
                html.append("<div class='connector'></div>")
        html.append("</div>")
        st.markdown("".join(html), unsafe_allow_html=True)

    st.subheader("Validation")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Validate Chain (external)"):
            ok, msg = ext_validate_chain(bc)
            if ok:
                st.success("Chain integrity validated")
                try:
                    bc.log_access("system", "VALIDATE_CHAIN", "-", True)
                except Exception:
                    pass
            else:
                st.error("Chain integrity failed")
                try:
                    bc.log_access("system", "VALIDATE_CHAIN", "-", False, reason=msg)
                except Exception:
                    pass
    with c2:
        if st.button("Validate Consensus"):
            ok, msg = validate_consensus_integrity(bc)
            if ok:
                st.success("Consensus integrity validated")
                try:
                    bc.log_access("system", "VALIDATE_CONSENSUS", "-", True)
                except Exception:
                    pass
            else:
                st.error("Consensus integrity failed")
                try:
                    bc.log_access("system", "VALIDATE_CONSENSUS", "-", False, reason=msg)
                except Exception:
                    pass


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
                # Log registration
                try:
                    st.session_state.bc.log_access(uid, "REGISTER_USER", uid, True)
                except Exception:
                    pass
                st.success("User registered")

        st.markdown("---")
        st.write("Users:")
        cols = st.columns(3)
        labels = {"doctors": "Doctors", "patients": "Patients", "admins": "Admins"}
        for i, role in enumerate(("doctors", "patients", "admins")):
            with cols[i]:
                st.markdown(f"### {labels[role]}")
                entries = bc.users[role]
                if role == "patients":
                    # Hide consent list from table, but show stake
                    rows = [{"id": x.get("id"), "name": x.get("name"), "stake": bc.get_stake(x.get("id"))} for x in entries]
                elif role == "doctors":
                    rows = [{"id": x.get("id"), "name": x.get("name"), "stake": bc.get_stake(x.get("id"))} for x in entries]
                else:
                    rows = [{"id": x.get("id"), "name": x.get("name")} for x in entries]
                if rows:
                    st.table(rows)
                else:
                    st.caption("No entries")

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
                        bc.save_state();
                        try:
                            bc.log_access(pid, "CONSENT_GIVE", did, True)
                        except Exception:
                            pass
                        st.success("Consent added")
                    else:
                        try:
                            bc.log_access(pid, "CONSENT_GIVE", did, False, reason="already_exists")
                        except Exception:
                            pass
                        st.warning("Consent already exists")
            with c2:
                if st.button("Revoke Consent"):
                    patient = next((p for p in bc.users["patients"] if p["id"] == pid), None)
                    if did in patient["consent"]:
                        patient["consent"].remove(did)
                        bc.save_state();
                        try:
                            bc.log_access(pid, "CONSENT_REVOKE", did, True)
                        except Exception:
                            pass
                        st.success("Consent revoked")
                    else:
                        try:
                            bc.log_access(pid, "CONSENT_REVOKE", did, False, reason="not_found")
                        except Exception:
                            pass
                        st.info("Nothing to revoke")


def consensus_page():
    bc = st.session_state.bc
    st.write("Consensus Mode: " + (bc.consensus_mode or "Not set"))
    # Show expected producer if available (winners-only scheduling)
    if bc.consensus_mode == "DPoS" and hasattr(bc, "current_expected_producer"):
        try:
            exp, winners = bc.current_expected_producer()
            if winners:
                st.info(f"Expected producer: {exp} | Winners (RR set): {', '.join(winners)}")
        except Exception:
            pass
    if st.button("Enable DPoS"):
        bc.consensus_mode = "DPoS"; bc.save_state(); st.success("DPoS enabled")
        try:
            bc.log_access("system", "CONSENSUS_ENABLE", "DPoS", True)
        except Exception:
            pass

    delegate_id = st.text_input("Add Delegate (ID)")
    if st.button("Add Delegate"):
        if not delegate_id or not bc.find_user(delegate_id):
            st.error("Delegate must be a registered user")
            try:
                bc.log_access(delegate_id or "", "DELEGATE_ADD", delegate_id or "", False, reason="not_registered")
            except Exception:
                pass
        elif hasattr(bc, "is_patient") and bc.is_patient(delegate_id):
            st.error("Patients cannot be delegates")
            try:
                bc.log_access(delegate_id, "DELEGATE_ADD", delegate_id, False, reason="patient_not_allowed")
            except Exception:
                pass
        elif delegate_id in bc.delegates:
            st.warning("Already a delegate")
            try:
                bc.log_access(delegate_id, "DELEGATE_ADD", delegate_id, False, reason="already_delegate")
            except Exception:
                pass
        else:
            bc.delegates.append(delegate_id)
            bc.save_state(); st.success("Delegate added")
            try:
                bc.log_access(delegate_id, "DELEGATE_ADD", delegate_id, True)
            except Exception:
                pass

    st.markdown("---")
    st.caption("Auto-select top-N delegates by stake (doctors only)")
    c1, c2 = st.columns([1,1])
    with c1:
        top_n = st.number_input("Number of delegates", min_value=1, value=max(1, len(bc.delegates) or 1), step=1)
    with c2:
        if st.button("Auto-Select Delegates by Stake"):
            # Rank doctors by stake (desc) and pick top N distinct IDs
            doctor_rows = bc.users.get("doctors", [])
            ranked = sorted(((d.get("id"), bc.get_stake(d.get("id"))) for d in doctor_rows), key=lambda x: x[1], reverse=True)
            new_delegates = [uid for uid, stake in ranked if stake > 0][: int(top_n)]
            before = list(bc.delegates)
            bc.delegates = new_delegates
            bc.save_state()
            st.success(f"Delegates set to: {', '.join(new_delegates) if new_delegates else '(none)'}")
            try:
                bc.log_access("system", "DELEGATES_AUTOSELECT", "-", True, before=before, after=new_delegates, top_n=int(top_n))
            except Exception:
                pass

    if bc.delegates:
        # Show delegates with their stakes
        label_list = [f"{d} (stake={bc.get_stake(d)})" for d in bc.delegates]
        st.write("Delegates:", ", ".join(label_list))
        to_remove = st.multiselect("Remove delegates", bc.delegates)
        if st.button("Remove Selected") and to_remove:
            bc.delegates = [d for d in bc.delegates if d not in to_remove]
            bc.save_state(); st.success("Removed selected delegates")
            try:
                for d in to_remove:
                    bc.log_access(d, "DELEGATE_REMOVE", d, True)
            except Exception:
                pass
    if st.button("Reset DPoS"):
        bc.consensus_mode = None; bc.delegates.clear(); bc.save_state(); st.info("DPoS reset")
        try:
            bc.log_access("system", "CONSENSUS_RESET", "DPoS", True)
        except Exception:
            pass

    st.markdown("---")
    st.subheader("Voting (Patients vote for Doctor Delegates)")
    # Voting form: patient chooses a doctor to vote for. Vote weight = patient stake.
    pat_ids = [p.get("id") for p in bc.users.get("patients", [])]
    doc_ids = [d.get("id") for d in bc.users.get("doctors", [])]
    if not pat_ids or not doc_ids:
        st.info("Register at least one patient and one doctor to enable voting.")
    else:
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            v_pid = st.selectbox("Patient (voter)", pat_ids, key="vote_pid")
            st.caption(f"Stake weight: {bc.get_stake(v_pid)}")
        with c2:
            v_did = st.selectbox("Doctor (candidate)", doc_ids, key="vote_did")
        with c3:
            if st.button("Cast Vote"):
                try:
                    if hasattr(bc, "set_vote"):
                        ok, msg = bc.set_vote(v_pid, v_did)
                    else:
                        # Local fallback: validate and update bc.votes
                        ok = True; msg = "Vote recorded"
                        if not (hasattr(bc, "is_patient") and bc.is_patient(v_pid)):
                            ok, msg = False, "Patient not found"
                        elif not (hasattr(bc, "is_doctor") and bc.is_doctor(v_did)):
                            ok, msg = False, "Doctor not found"
                        if ok:
                            if not hasattr(bc, "votes") or bc.votes is None:
                                bc.votes = {}
                            bc.votes[v_pid] = v_did
                    if ok:
                        bc.save_state(); st.success("Vote recorded")
                        try:
                            bc.log_access(v_pid, "VOTE_CAST", v_did, True, weight=bc.get_stake(v_pid))
                        except Exception:
                            pass
                    else:
                        st.error(msg)
                        try:
                            bc.log_access(v_pid, "VOTE_CAST", v_did, False, reason=msg)
                        except Exception:
                            pass
                except Exception as e:
                    st.error(f"Failed to cast vote: {e}")
                    try:
                        bc.log_access(v_pid, "VOTE_CAST", v_did, False, reason=str(e))
                    except Exception:
                        pass

    # Show weighted tally
    tally = bc.tally_votes() if hasattr(bc, "tally_votes") else {}
    if tally:
        rows = []
        for did, meta in tally.items():
            rows.append({
                "doctor": did,
                "weight": round(float(meta.get("weight", 0.0)), 4),
                "votes": int(meta.get("count", 0)),
                "stake": bc.get_stake(did),
                "is_current_delegate": did in bc.delegates,
            })
        st.table(sorted(rows, key=lambda r: (-r["weight"], r["doctor"])) )
    else:
        st.caption("No votes yet.")

    # Select delegates from votes with tie-breaker
    c1, c2 = st.columns([1,1])
    with c1:
        top_n_votes = st.number_input("Delegates to select from votes", min_value=1, value=max(1, len(bc.delegates) or 1), step=1)
    with c2:
        if st.button("Select Delegates from Votes"):
            try:
                if hasattr(bc, "select_delegates_from_votes"):
                    new_delegates = bc.select_delegates_from_votes(int(top_n_votes), prefer_existing=True)
                else:
                    # Fallback: compute selection locally if method missing
                    votes = getattr(bc, "votes", {}) or {}
                    doctor_ids = {d.get("id") for d in bc.users.get("doctors", [])}
                    # Tally weights by doctor (sum of patient stakes)
                    weights = {}
                    for pid, did in votes.items():
                        if did not in doctor_ids:
                            continue
                        w = 0.0
                        if hasattr(bc, "get_stake"):
                            try:
                                w = float(bc.get_stake(pid))
                            except Exception:
                                w = 0.0
                        weights[did] = weights.get(did, 0.0) + w
                    old_set = set(bc.delegates)
                    ranked = sorted(weights.items(), key=lambda kv: (-kv[1], ('' if kv[0] in old_set else 'z'), kv[0]))
                    new_delegates = [did for did, _ in ranked[: int(top_n_votes)]]
                    bc.delegates = new_delegates
                bc.save_state()
                st.success(f"Delegates from votes: {', '.join(new_delegates) if new_delegates else '(none)'}")
                try:
                    bc.log_access("system", "DELEGATES_FROM_VOTES", "-", True, selected=new_delegates, top_n=int(top_n_votes))
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Failed to select delegates from votes: {e}")
                try:
                    bc.log_access("system", "DELEGATES_FROM_VOTES", "-", False, reason=str(e))
                except Exception:
                    pass


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
            # Enforce winners-only producer if DPoS
            if bc.consensus_mode == "DPoS" and hasattr(bc, "current_expected_producer"):
                try:
                    exp, winners = bc.current_expected_producer()
                    if winners and doctor_id != exp:
                        st.error(f"Only current expected producer can add a block right now. Expected: {exp}")
                        try:
                            bc.log_access(doctor_id, "WRITE", record_id, False, reason="not_current_producer", expected=exp)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
            blk = bc.add_block_with_consensus([tx])
            if blk:
                st.success(f"Added in block {blk.index}")
                # Log successful write with rich metadata
                try:
                    bc.log_access(
                        doctor_id,
                        "WRITE",
                        record_id.strip(),
                        True,
                        record_type=record_type,
                        operation=operation,
                        amount=amount.strip(),
                        hospital_id=hospital_id.strip(),
                        insurance_id=insurance_id.strip(),
                        patient_id=patient_id.strip(),
                        block_index=blk.index,
                    )
                except Exception:
                    pass
                bc.save_state()
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
                st.error("Invalid code");
                try:
                    bc.log_access(ed.strip(), "EMERGENCY_WRITE", er.strip(), False, reason="invalid_code", hospital_id=eh.strip(), patient_id=ep.strip(), insurance_id=ei.strip(), amount=ea.strip())
                except Exception:
                    pass
                return
            # Enforce winners-only producer for emergency as well
            if bc.consensus_mode == "DPoS" and hasattr(bc, "current_expected_producer"):
                try:
                    exp, winners = bc.current_expected_producer()
                    if winners and ed.strip() != exp:
                        st.error(f"Only current expected producer can add a block right now. Expected: {exp}")
                        try:
                            bc.log_access(ed.strip(), "EMERGENCY_WRITE", er.strip(), False, reason="not_current_producer", expected=exp)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
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
                try:
                    bc.log_access(ed.strip(), "EMERGENCY_WRITE", er.strip(), True, reason="emergency_override", block_index=blk.index, hospital_id=eh.strip(), patient_id=ep.strip(), insurance_id=ei.strip(), amount=ea.strip())
                except Exception:
                    pass
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
    # Compute consent status for displayed block based on current patient consents
    def _consent_status_for_block(block) -> str:
        granted = 0
        missing = 0
        for t in (block.transactions or []):
            did = t.get("doctor_id"); pid = t.get("patient_id")
            if not did or not pid:
                continue
            patient = next((p for p in bc.users.get("patients", []) if p.get("id") == pid), None)
            if patient and did in patient.get("consent", []):
                granted += 1
            else:
                missing += 1
        if granted == 0 and missing == 0:
            return "-"
        if missing == 0:
            return "Granted"
        if granted == 0:
            return "Not granted"
        return "Partial"
    consent_status = _consent_status_for_block(blk)
    c1, c2 = st.columns(2)
    with c1:
        st.write("Index:", blk.index)
        st.write("Timestamp:", blk.timestamp)
        st.write("Prev Hash:", blk.prev_hash)
        st.write("Merkle Root:", blk.merkle_root)
        st.write("Hash:", blk.hash())
        st.write("Consent:", consent_status)
    with c2:
        st.write("Consensus:", json.dumps(blk.consensus_data, indent=2))
    st.write("Transactions:")
    for i, tx in enumerate(blk.transactions):
        with st.expander(f"{tx.get('record_id','?')}"):
            st.code(json.dumps(tx, indent=2), language="json")


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
        # Producer stake (if any)
        p_stake = bc.get_stake(producer) if producer and producer != "-" else 0
        # Derive action and reason from transactions
        action = "No transactions"
        reason = "-"
        txs = blk.transactions or []
        if txs:
            if len(txs) == 1:
                t = txs[0]
                op = t.get("operation", "?")
                rid = t.get("record_id", "?")
                action = f"{op} {rid}"
                reason_map = {
                    "Add": "New record added",
                    "Update": "Record updated",
                    "Share": "Record shared",
                    "Emergency_Add": "Emergency record added",
                    "Delete": "Record deleted",
                }
                reason = reason_map.get(op, "Transaction included")
            else:
                unique_ops = sorted({t.get("operation", "?") for t in txs})
                action = f"{len(txs)} transactions"
                reason = ", ".join(unique_ops)
        # Compute consent summary for this block
        consent = "-"
        if txs:
            granted = 0; missing = 0
            for t in txs:
                did = t.get("doctor_id"); pid = t.get("patient_id")
                if not did or not pid:
                    continue
                patient = next((p for p in bc.users.get("patients", []) if p.get("id") == pid), None)
                if patient and did in patient.get("consent", []):
                    granted += 1
                else:
                    missing += 1
            if missing == 0 and granted > 0:
                consent = "Granted"
            elif granted == 0 and missing > 0:
                consent = "Not granted"
            elif granted > 0 and missing > 0:
                consent = "Partial"
        node = textwrap.dedent(f"""
        <div class='chain-node'>
            <h4>BLOCK {blk.index}</h4>
            <div class='kv'>time: {blk.timestamp}</div>
            <div class='kv'>prev: {fmt(blk.prev_hash)}</div>
            <div class='kv'>hash: {fmt(bhash)}</div>
            <div class='kv'>merkle: {fmt(blk.merkle_root)}</div>
            <div class='kv'>mode: {mode} | delegate: {producer} (stake={p_stake})</div>
            <div class='kv'>action: {action}</div>
            <div class='kv'>reason: {reason}</div>
            <div class='kv'>consent: {consent}</div>
        </div>
        """)
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
    st.subheader("Admin")
    # If no blocks exist yet, allow creating the genesis block here
    if not bc.chain:
        st.info("No blocks found. Create a genesis block to initialize the chain.")
        if st.button("Create Genesis Block"):
            bc.create_genesis(); bc.save_state(); st.success("Genesis created")
            try:
                bc.log_access("system", "GENESIS_CREATE", "-", True)
            except Exception:
                pass
    t1, t2 = st.tabs(["Register User", "Staking"])

    # Tab 1: Register User (Admin can register doctors/patients/admins)
    with t1:
        role = st.selectbox("Role", ["doctor", "patient", "admin"], key="admin_reg_role")
        uid = st.text_input("ID", key="admin_reg_id")
        name = st.text_input("Name", key="admin_reg_name")
        if st.button("Register", key="admin_btn_register"):
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
                bc.save_state(); st.success("User registered")
                try:
                    bc.log_access(uid, "REGISTER_USER", uid, True, role=role)
                except Exception:
                    pass

        st.markdown("---")
        st.caption("Current users")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("Doctors")
            st.table(bc.users.get("doctors", []))
        with c2:
            st.write("Patients")
            st.table([{k: v for k, v in p.items() if k != "consent"} for p in bc.users.get("patients", [])])
        with c3:
            st.write("Admins")
            st.table(bc.users.get("admins", []))

    # Tab 2: Staking (Admin assigns stake to doctor/patient)
    with t2:
        st.caption("Assign stake to a doctor or patient. Stake is a numeric weight used by DPoS.")
        # Build selectable list of all non-admin users
        all_users = (
            [(d["id"], f"Doctor: {d['id']} - {d['name']}") for d in bc.users.get("doctors", [])]
            + [(p["id"], f"Patient: {p['id']} - {p['name']}") for p in bc.users.get("patients", [])]
        )
        if not all_users:
            st.info("No doctors or patients registered yet.")
        else:
            user_options = {uid: label for uid, label in all_users}
            selected_uid = st.selectbox("Select User", list(user_options.keys()), format_func=lambda k: user_options[k])
            current_stake = bc.get_stake(selected_uid)
            st.write(f"Current stake: {current_stake}")
            new_stake = st.text_input("New stake (number)", value=str(current_stake), key="stake_input")
            c1, c2 = st.columns([1,1])
            with c1:
                if st.button("Set Stake", key="btn_set_stake"):
                    ok, msg = bc.set_stake(selected_uid, new_stake)
                    if ok:
                        bc.save_state(); st.success("Stake updated")
                        try:
                            role = "doctor" if bc.is_doctor(selected_uid) else ("patient" if bc.is_patient(selected_uid) else "-")
                            bc.log_access("admin", "STAKE_SET", selected_uid, True, role=role, stake=float(new_stake))
                        except Exception:
                            pass
                    else:
                        st.error(msg)
                        try:
                            bc.log_access("admin", "STAKE_SET", selected_uid, False, reason=msg)
                        except Exception:
                            pass
            with c2:
                if st.button("Clear Stake", key="btn_clear_stake"):
                    ok, msg = bc.set_stake(selected_uid, 0)
                    if ok:
                        bc.save_state(); st.info("Stake cleared")
                        try:
                            role = "doctor" if bc.is_doctor(selected_uid) else ("patient" if bc.is_patient(selected_uid) else "-")
                            bc.log_access("admin", "STAKE_SET", selected_uid, True, role=role, stake=0)
                        except Exception:
                            pass
                    else:
                        st.error(msg)

        st.markdown("---")
        st.caption("Current stakes")
        # Build stakes table
        stake_rows = []
        for role_name in ("doctors", "patients"):
            for u in bc.users.get(role_name, []):
                stake_rows.append({
                    "id": u.get("id"),
                    "name": u.get("name"),
                    "role": "doctor" if role_name == "doctors" else "patient",
                    "stake": bc.get_stake(u.get("id")),
                })
        if stake_rows:
            st.table(stake_rows)
        else:
            st.info("No stakes assigned yet.")

    # Note: Logs are available in the dedicated Logs page


def logs_page():
    bc = st.session_state.bc
    st.subheader("Access Logs")
    if not bc.access_logs:
        st.info("No logs yet. Perform some actions (write records, give/revoke consent) to generate logs.")
        return

    # Filters
    actions = sorted({e.get("action", "-") for e in bc.access_logs})
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        sel_actions = st.multiselect("Actions", actions, default=actions)
    with c2:
        user_q = st.text_input("User contains")
    with c3:
        record_q = st.text_input("Record contains")
    with c4:
        status = st.selectbox("Status", ["All", "Success", "Failed"], index=0)

    # Apply filters (newest first)
    logs = list(reversed(bc.access_logs[-500:]))
    def _match(e: dict) -> bool:
        if sel_actions and e.get("action") not in sel_actions:
            return False
        if user_q and user_q.lower() not in str(e.get("user_id", "")).lower():
            return False
        if record_q and record_q.lower() not in str(e.get("record_id", "")).lower():
            return False
        if status == "Success" and not e.get("success", False):
            return False
        if status == "Failed" and e.get("success", False):
            return False
        return True
    logs = [e for e in logs if _match(e)]

    # Summary
    st.caption(f"Showing {len(logs)} log(s)")
    if not logs:
        st.info("No logs match the filters.")
        return

    # Pretty cards with all fields
    for e in logs:
        ok = bool(e.get("success"))
        badge = "✅ Success" if ok else "❌ Failed"
        # Build key-value HTML for all fields except timestamp/success (shown separately)
        rows = []
        for k, v in sorted(e.items()):
            if k in ("timestamp", "success"):
                continue
            rows.append(f"<div class='kv'>{k}: {v}</div>")
        body_html = "\n".join(rows)
        st.markdown(
            textwrap.dedent(
                f"""
                <div class='log-card'>
                    <div class='log-head'>
                        <span class='log-time'>{e.get('timestamp','')}</span>
                        <span class='log-badge {'ok' if ok else 'fail'}'>{badge}</span>
                    </div>
                    {body_html}
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        with st.expander("Details (JSON)"):
            st.code(json.dumps(e, indent=2), language="json")

    # Export buttons
    json_bytes = json.dumps(logs, indent=2).encode("utf-8")
    st.download_button(
        "Download Logs (JSON)", data=json_bytes, file_name="access_logs.json", mime="application/json"
    )

    # Build CSV export
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
    st.download_button(
        "Download Logs (CSV)", data=csv_bytes, file_name="access_logs.csv", mime="text/csv"
    )


def main():
    init_app_state()
    app_header()
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Users", "Records", "Consensus", "Explorer", "Chain", "Logs", "Admin"],
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
    elif page == "Logs":
        logs_page()
    else:
        admin_page()


if __name__ == "__main__":
    main()
