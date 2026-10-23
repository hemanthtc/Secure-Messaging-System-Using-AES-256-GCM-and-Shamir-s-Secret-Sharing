"""
Cryptographically Secure Random Source Module
Provides CSPRNG utilities backed by os.urandom / secrets module.
Never uses deterministic or pseudo-random linear congruential generators.
"""

import secrets

def get_random_field_element(prime: int) -> int:
    """Generate a uniform random integer in the range [0, prime - 1]."""
    return secrets.randbelow(prime)

def get_random_nonzero_field_element(prime: int) -> int:
    """Generate a uniform random non-zero integer in the range [1, prime - 1]."""
    val = 0
    while val == 0:
        val = secrets.randbelow(prime)
    return val

def get_random_bytes(num_bytes: int) -> bytes:
    """Generate cryptographically secure random byte sequence."""
    return secrets.token_bytes(num_bytes)
