"""
Shamir's Secret Sharing Automated Unit Tests
Verifies finite field arithmetic, polynomial evaluation, Lagrange interpolation,
threshold (K, M) recovery, failure with insufficient shares, and rejection of conflicting shares.
"""

import pytest
import os
from app.crypto.finite_field import PrimeField, field
from app.crypto.interpolation import evaluate_polynomial, lagrange_interpolate_zero
from app.crypto.shamir import split_secret, recover_secret
from app.crypto.key_management import create_message_key_shares, reconstruct_aes_key_from_shares

def test_finite_field_basic_arithmetic():
    """Test addition, subtraction, multiplication, and inverse in F_p."""
    f = PrimeField()
    a = 123456789
    b = 987654321

    # Inverses
    inv_a = f.inv(a)
    assert f.mul(a, inv_a) == 1

    # Add / Sub
    sum_ab = f.add(a, b)
    assert f.sub(sum_ab, b) == a

    # Div
    div_ab = f.div(a, b)
    assert f.mul(div_ab, b) == a

def test_shamir_threshold_k_recovery_exact():
    """Test splitting a 32-byte secret into M=5 shares with threshold K=3, and recovering using exactly K shares."""
    secret = os.urandom(32)
    k = 3
    m = 5

    shares = split_secret(secret, k, m)
    assert len(shares) == m

    # Recover using exactly first K shares
    subset_k = shares[:k]
    recovered = recover_secret(subset_k, k_threshold=k)
    assert recovered == secret

def test_shamir_all_m_shares_recovery():
    """Test recovering using all M shares."""
    secret = os.urandom(32)
    k = 3
    m = 7

    shares = split_secret(secret, k, m)
    recovered = recover_secret(shares, k_threshold=k)
    assert recovered == secret

def test_shamir_arbitrary_k_subset_recovery():
    """Test recovering using arbitrary combination of K shares (e.g. shares at index 1, 3, 5)."""
    secret = os.urandom(32)
    k = 4
    m = 8

    shares = split_secret(secret, k, m)
    # Pick shares 2, 4, 6, 8 (0-indexed: 1, 3, 5, 7)
    arbitrary_subset = [shares[1], shares[3], shares[5], shares[7]]
    recovered = recover_secret(arbitrary_subset, k_threshold=k)
    assert recovered == secret

def test_shamir_insufficient_shares_fails():
    """Test that attempting recovery with K - 1 shares is rejected."""
    secret = os.urandom(32)
    k = 4
    m = 6

    shares = split_secret(secret, k, m)
    subset_k_minus_1 = shares[: k - 1]  # Only 3 shares, need 4

    with pytest.raises(ValueError, match="Insufficient shares for recovery"):
        recover_secret(subset_k_minus_1, k_threshold=k)

def test_shamir_conflicting_shares_rejected():
    """Test that supplying two different y coordinates for the same x coordinate is rejected."""
    secret = os.urandom(32)
    k = 3
    m = 5
    shares = split_secret(secret, k, m)

    # Corrupt share with duplicate x=1 but different y
    conflicting_shares = [shares[0], (1, shares[0][1] + 999), shares[1], shares[2]]
    with pytest.raises(ValueError, match="Conflicting share coordinates"):
        recover_secret(conflicting_shares, k_threshold=k)

def test_key_management_serialization_roundtrip():
    """Test serialization to dictionaries with hex strings and subsequent key reconstruction."""
    secret_key = os.urandom(32)
    shares_dicts = create_message_key_shares(secret_key, k=3, m=5)
    assert len(shares_dicts) == 5

    # Reconstruct from subset of 3 share dicts
    subset_dicts = shares_dicts[1:4]
    reconstructed_key = reconstruct_aes_key_from_shares(subset_dicts, k_threshold=3)
    assert reconstructed_key == secret_key
