"""
Shamir's Secret Sharing Scheme Module
Implements threshold-based cryptographic secret sharing over finite field F_p.
Separates key-share operations strictly from payload fragmentation.
"""

from typing import List, Tuple
from app.crypto.finite_field import PrimeField, field
from app.crypto.interpolation import evaluate_polynomial, lagrange_interpolate_zero
from app.crypto.random_source import get_random_field_element
from app.validators.share_validator import validate_sss_parameters

def split_secret(secret_bytes: bytes, k: int, m: int, f: PrimeField = field) -> List[Tuple[int, int]]:
    """
    Split a 32-byte secret into M shares with reconstruction threshold K (2 <= K <= M <= 10).
    Returns a list of M tuples: [(1, y_1), (2, y_2), ..., (M, y_M)].
    """
    is_valid, k_val, m_val, err = validate_sss_parameters(k, m)
    if not is_valid:
        raise ValueError(f"Invalid SSS parameters: {err}")

    if not secret_bytes:
        raise ValueError("Secret bytes cannot be empty.")

    # Convert secret bytes into integer in F_p
    secret_int = int.from_bytes(secret_bytes, byteorder="big")
    if secret_int >= f.p:
        raise ValueError("Secret magnitude exceeds finite field characteristic.")

    # Generate K - 1 cryptographically secure random coefficients
    coefficients = [secret_int]
    for _ in range(k_val - 1):
        coefficients.append(get_random_field_element(f.p))

    # Evaluate polynomial at evaluation points x = 1 .. M
    shares = []
    for x in range(1, m_val + 1):
        y = evaluate_polynomial(coefficients, x, f)
        shares.append((x, y))

    return shares

def recover_secret(shares: List[Tuple[int, int]], k_threshold: int, expected_byte_len: int = 32, f: PrimeField = field) -> bytes:
    """
    Reconstruct the secret using any subset of at least K valid distinct shares.
    Rejects malformed or duplicate share coordinates.
    """
    if k_threshold < 2:
        raise ValueError("Key recovery threshold K must be at least 2.")

    if not shares:
        raise ValueError("No shares provided for reconstruction.")

    # Deduplicate shares by x coordinate while detecting inconsistent y values
    unique_shares = {}
    for x, y in shares:
        if x in unique_shares:
            if unique_shares[x] != y:
                raise ValueError(f"Conflicting share coordinates detected for x={x}.")
        else:
            unique_shares[x] = y

    if len(unique_shares) < k_threshold:
        raise ValueError(
            f"Insufficient shares for recovery: received {len(unique_shares)} unique shares, "
            f"threshold K requires {k_threshold}."
        )

    # Use the first K unique shares to perform Lagrange interpolation
    subset = list(unique_shares.items())[:k_threshold]
    reconstructed_int = lagrange_interpolate_zero(subset, f)

    # Convert back to standard byte array
    return reconstructed_int.to_bytes(expected_byte_len, byteorder="big")
