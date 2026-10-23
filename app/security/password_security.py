"""
Password Security Module
Implements Argon2id password hashing and verification with fallback to scrypt.
Plaintext passwords are never stored or logged.
"""

import hmac
import hashlib
import os

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
    _ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)
    _USE_ARGON2 = True
except ImportError:
    _USE_ARGON2 = False

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id or secure scrypt."""
    if not password:
        raise ValueError("Password cannot be empty.")

    if _USE_ARGON2:
        return _ph.hash(password)
    else:
        # Standard library scrypt fallback
        salt = os.urandom(16)
        h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, maxmem=67108864)
        return f"scrypt$16384$8$1${salt.hex()}${h.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored hash using constant-time comparison."""
    if not password or not hashed_password:
        return False

    if _USE_ARGON2 and hashed_password.startswith("$argon2"):
        try:
            return _ph.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError):
            return False
        except Exception:
            return False

    if hashed_password.startswith("scrypt$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) != 6:
                return False
            _, n_str, r_str, p_str, salt_hex, hash_hex = parts
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            computed_hash = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n_str),
                r=int(r_str),
                p=int(p_str),
                maxmem=67108864
            )
            return hmac.compare_digest(computed_hash, expected_hash)
        except Exception:
            return False

    return False
