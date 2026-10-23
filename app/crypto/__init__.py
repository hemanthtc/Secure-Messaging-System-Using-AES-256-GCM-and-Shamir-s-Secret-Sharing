"""
Cryptography package initialization.
"""

from app.crypto.finite_field import PrimeField, field
from app.crypto.interpolation import evaluate_polynomial, lagrange_interpolate_zero
from app.crypto.random_source import get_random_field_element, get_random_bytes
from app.crypto.shamir import split_secret, recover_secret
from app.crypto.encryption import encrypt_message, decrypt_message
from app.crypto.hashing import sha256_bytes, sha256_text
from app.crypto.key_management import (
    create_message_key_shares,
    reconstruct_aes_key_from_shares,
    export_shares_to_dict,
    parse_shares_from_dict,
)

__all__ = [
    "PrimeField",
    "field",
    "evaluate_polynomial",
    "lagrange_interpolate_zero",
    "get_random_field_element",
    "get_random_bytes",
    "split_secret",
    "recover_secret",
    "encrypt_message",
    "decrypt_message",
    "sha256_bytes",
    "sha256_text",
    "create_message_key_shares",
    "reconstruct_aes_key_from_shares",
    "export_shares_to_dict",
    "parse_shares_from_dict",
]
