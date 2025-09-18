"""
Healthcare Blockchain System

A modular blockchain implementation for healthcare record management
with multiple consensus mechanisms and comprehensive validation.
"""

__version__ = "1.0.0"
__author__ = "Healthcare Blockchain Team"

from .blockchain import Blockchain, Block
from .user_management import register_user, give_consent
from .transactions import input_transaction, validate_transaction_data
from .consensus import configure_consensus
from .views import show_chain, view_access_logs, view_record_history
from .validation import validate_chain_integrity, validate_consensus_integrity
from .helpers import compute_transaction_fingerprint, build_merkle_tree_root

__all__ = [
    "Blockchain",
    "Block", 
    "register_user",
    "give_consent",
    "input_transaction",
    "validate_transaction_data",
    "configure_consensus",
    "show_chain",
    "view_access_logs", 
    "view_record_history",
    "validate_chain_integrity",
    "validate_consensus_integrity",
    "compute_transaction_fingerprint",
    "build_merkle_tree_root"
]
