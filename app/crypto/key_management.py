"""
Key Management Module
Provides key lifecycle utilities, serialization, and coordinate formatting
for standard AES keys and Shamir's Secret Sharing shares.
"""

import base64
from typing import List, Tuple, Dict, Any
from app.crypto.shamir import split_secret, recover_secret

def export_shares_to_dict(shares: List[Tuple[int, int]]) -> List[Dict[str, Any]]:
    """Convert list of (x, y) integer tuples into serializable dictionary format with hex y values."""
    return [
        {
            "share_index": idx + 1,
            "share_x": x,
            "share_y": hex(y),
        }
        for idx, (x, y) in enumerate(shares)
    ]

def parse_shares_from_dict(share_dicts: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """Parse share dictionaries back into integer tuples (x, y)."""
    shares = []
    for item in share_dicts:
        x = int(item["share_x"])
        y_val = item["share_y"]
        y = int(y_val, 16) if isinstance(y_val, str) and y_val.startswith("0x") else int(y_val)
        shares.append((x, y))
    return shares

def create_message_key_shares(aes_key: bytes, k: int, m: int) -> List[Dict[str, Any]]:
    """Split AES key using Shamir's Secret Sharing into M shares with threshold K."""
    shares = split_secret(aes_key, k, m)
    return export_shares_to_dict(shares)

def reconstruct_aes_key_from_shares(share_dicts: List[Dict[str, Any]], k_threshold: int) -> bytes:
    """Reconstruct 32-byte AES key from received shares."""
    parsed_shares = parse_shares_from_dict(share_dicts)
    return recover_secret(parsed_shares, k_threshold, expected_byte_len=32)
