# DPoS Consensus Implementation

try:
    from .blockchain import Blockchain
except ImportError:
    pass


def configure_consensus(bc):
    print("\nSetting up DPoS Consensus")
    configure_dpos(bc)




def configure_dpos(bc):
    bc.consensus_mode = "DPoS"
    print("Setting up delegates for DPoS")

    delegates = []
    while True:
        did = input("Enter delegate ID (press enter when done): ").strip()
        if not did:
            break

        if not bc.find_user(did):
            print("Error: user does not exist. Register first.")
            continue

        # Patients cannot be delegates
        if hasattr(bc, 'is_patient') and bc.is_patient(did):
            print("Error: patients cannot be delegates. Choose a doctor/admin.")
            continue

        if did in delegates:
            print("Error: delegate already added.")
            continue

        delegates.append(did)
        print(f"Added delegate: {did}")

    bc.delegates = delegates
    if delegates:
        print(f"DPoS configured with {len(delegates)} delegates: {delegates}")
    else:
        print("No delegates selected. DPoS needs delegates to work.")


def reset_consensus(bc: 'Blockchain'):
    bc.consensus_mode = None
    bc.delegates.clear()
    print("DPoS consensus configuration reset.")
