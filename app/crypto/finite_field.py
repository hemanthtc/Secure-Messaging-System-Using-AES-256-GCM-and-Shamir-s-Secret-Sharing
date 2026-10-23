"""
Finite Field Arithmetic Module
Implements Galois Field arithmetic over prime field F_p.
Using the 257-bit prime p = 2^256 + 297, every 256-bit AES key fits naturally
in F_p without modular truncation or precision loss.
"""

class PrimeField:
    """Field arithmetic over prime modulus p."""

    # Smallest prime greater than 2^256: 2^256 + 297
    DEFAULT_PRIME = 115792089237316195423570985008687907853269984665640564039457584007913129640233

    def __init__(self, p: int = DEFAULT_PRIME):
        self.p = p

    def add(self, a: int, b: int) -> int:
        """Addition in F_p: (a + b) mod p."""
        return (a + b) % self.p

    def sub(self, a: int, b: int) -> int:
        """Subtraction in F_p: (a - b) mod p."""
        return (a - b) % self.p

    def mul(self, a: int, b: int) -> int:
        """Multiplication in F_p: (a * b) mod p."""
        return (a * b) % self.p

    def inv(self, a: int) -> int:
        """Multiplicative inverse in F_p using Fermat's Little Theorem: a^(p-2) mod p."""
        if a % self.p == 0:
            raise ZeroDivisionError("Cannot invert zero in finite field.")
        return pow(a % self.p, self.p - 2, self.p)

    def div(self, a: int, b: int) -> int:
        """Division in F_p: (a * b^-1) mod p."""
        return self.mul(a, self.inv(b))

# Default singleton field instance
field = PrimeField()
