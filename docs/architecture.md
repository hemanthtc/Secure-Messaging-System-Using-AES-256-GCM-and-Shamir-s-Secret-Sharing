# SecureShare Messenger - Architecture Document

## Overview
SecureShare Messenger implements a defense-in-depth messaging architecture combining byte-level payload fragmentation and cryptographic secret sharing.

### Cryptographic Pipeline
1. **Plaintext Input:** UTF-8 encoded string (up to 64 KB).
2. **AES-256-GCM Encryption:** Encrypts payload with a 256-bit key and 12-byte random nonce, generating ciphertext and a 16-byte authentication tag.
3. **Fragmentation Engine:** Slices ciphertext into $N \in [2, 10]$ chunks using integer division ($q = L // N, r = L \% N$).
4. **Shamir's Secret Sharing (Optional):** Evaluates a polynomial of degree $K-1$ over prime field $\mathbb{F}_p$ ($p = 2^{256} + 297$), distributing $M$ shares of the 256-bit AES key.
5. **Reassembly Pipeline:** Buffers arriving fragments, validates indices ($1 \le i \le N$), verifies SHA-256 hashes, deduplicates repeated packets, and reconstructs the payload only when all $N$ fragments are present.
