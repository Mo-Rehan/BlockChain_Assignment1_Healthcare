# Healthcare Record Management System (Blockchain)

Language: Python

Consensus Algorithm: Delegated Proof of Stake (DPoS)

This program manages patient records on a simple blockchain. Only verified blocks are added. DPoS is the only consensus used. Patients cannot be delegates.

Features
- User registration: doctor, patient, admin
- Patient consent for doctors
- Add/view medical records
- DPoS consensus (round-robin delegates)
- Merkle root per block
- Access logs

How to run (CLI)
1) Install requirements (Python 3.8+):
   pip install -r requirements.txt
2) Start the CLI:
   python -m src.main

How to run (Streamlit)
1) Install requirements (Python 3.8+):
   pip install -r requirements.txt
2) Start the CLI:
   python -m src.gui

Basic steps
1) Create genesis
2) Register users
3) Give patient consent to a doctor
4) Configure DPoS and add delegates (only doctors/admins)
5) Add a medical record block
6) View chain, record history, and logs

Files (short)
- src/blockchain.py      Core classes and block verification
- src/consensus.py       DPoS configuration
- src/validation.py      Validation rules (transactions, chain, DPoS)
- src/transactions.py    Transaction input helpers
- src/user_management.py Registration and consent
- src/views.py           Simple views for CLI
- src/helpers.py         Hash/Merkle helpers
- src/main.py            CLI menu

Notes
- Only DPoS is supported.
- Patients cannot be delegates or block producers.
- The code stores state in data/blockchain.json
