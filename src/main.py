# Healthcare Blockchain CLI Application
try:
    from .blockchain import Blockchain
    from .user_management import register_user as register_healthcare_participant, give_consent
    from .transactions import input_transaction as create_medical_record_transaction
    from .consensus import configure_consensus
    from .views import show_chain, view_access_logs, view_record_history
except ImportError:
    from blockchain import Blockchain
    from user_management import register_user as register_healthcare_participant, give_consent
    from transactions import input_transaction as create_medical_record_transaction
    from consensus import configure_consensus
    from views import show_chain, view_access_logs, view_record_history


def main():
    bc = Blockchain()
    bc.load_state()

    print("Healthcare Blockchain CLI")

    while True:
        print("\n--- Main Menu ---")
        print("1. Create Genesis Block")
        print("2. Register User (Doctor/Patient/Admin)")
        print("3. Give Patient Consent")
        print("4. Configure DPoS Consensus")
        print("5. Add Medical Record Block (Doctor action)")
        print("6. View Record History")
        print("7. View Access Logs (admin)")
        print("8. Show Blockchain")
        print("9. List Registered Users")
        print("10. Validate Blockchain Integrity")
        print("11. Fix Blockchain Integrity")
        print("12. Save & Exit")

        choice = input("Choose option: ").strip()
        if choice == "1":
            bc.create_genesis()
        elif choice == "2":
            register_healthcare_participant(bc)
        elif choice == "3":
            give_consent(bc)
        elif choice == "4":
            configure_consensus(bc)
        elif choice == "5":
            if not bc.chain:
                print("Create genesis block first.")
                continue
            tx = create_medical_record_transaction(bc)
            if tx:
                bc.add_block_with_consensus([tx])
        elif choice == "6":
            view_record_history(bc)
        elif choice == "7":
            view_access_logs(bc)
        elif choice == "8":
            show_chain(bc)
        elif choice == "9":
            bc.list_users()
        elif choice == "10":
            bc.validate_chain()
        elif choice == "11":
            bc.fix_chain_integrity()
        elif choice == "12":
            bc.save_state()
            print("Blockchain state saved to data/blockchain.json")
            print("Exiting.")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
