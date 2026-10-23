"""
Cryptographic Hashing Utilities Module
Implements SHA-256 integrity verification for fragments and full ciphertext payloads.
"""

import hashlib

def sha256_bytes(data: bytes) -> str:
    """Compute lowercase SHA-256 hexadecimal digest of byte data."""
    return hashlib.sha256(data).hexdigest()

def sha256_text(text: str) -> str:
    """Compute lowercase SHA-256 hexadecimal digest of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
