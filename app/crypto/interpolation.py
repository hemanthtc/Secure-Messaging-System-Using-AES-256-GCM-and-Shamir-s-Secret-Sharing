"""
Polynomial Evaluation and Lagrange Interpolation Module
Implements deterministic polynomial evaluation and Lagrange interpolation over finite field F_p.
Used to recover the secret constant term P(0) from K shares.
"""

from typing import List, Tuple
from app.crypto.finite_field import PrimeField, field

def evaluate_polynomial(coefficients: List[int], x: int, f: PrimeField = field) -> int:
    """
    Evaluate polynomial P(x) = sum_{i=0}^{k-1} a_i * x^i mod p using Horner's method.
    coefficients: [a_0, a_1, ..., a_{k-1}] where a_0 is the secret constant.
    """
    result = 0
    # Horner's rule from highest degree to lowest
    for coeff in reversed(coefficients):
        result = f.add(f.mul(result, x), coeff)
    return result

def lagrange_interpolate_zero(points: List[Tuple[int, int]], f: PrimeField = field) -> int:
    """
    Reconstruct secret P(0) from a list of points (x_i, y_i) via Lagrange interpolation.
    Points must have distinct x coordinates.
    Formula:
        P(0) = sum_{j=1}^K [ y_j * prod_{m != j} ( -x_m / (x_j - x_m) ) ] mod p
    """
    if not points:
        raise ValueError("Points list cannot be empty.")

    # Validate unique non-zero x coordinates
    x_seen = set()
    for x, _ in points:
        if x == 0:
            raise ValueError("Share coordinate x cannot be zero.")
        if x in x_seen:
            raise ValueError(f"Duplicate share coordinate x={x} detected.")
        x_seen.add(x)

    secret = 0
    for j, (xj, yj) in enumerate(points):
        # Compute Lagrange basis polynomial L_j(0)
        numerator = 1
        denominator = 1
        for m, (xm, _) in enumerate(points):
            if m == j:
                continue
            # (-xm)
            numerator = f.mul(numerator, f.sub(0, xm))
            # (xj - xm)
            denominator = f.mul(denominator, f.sub(xj, xm))

        basis = f.div(numerator, denominator)
        term = f.mul(yj, basis)
        secret = f.add(secret, term)

    return secret
