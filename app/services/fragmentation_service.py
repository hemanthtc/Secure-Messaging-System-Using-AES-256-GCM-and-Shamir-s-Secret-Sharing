"""
Message Fragmentation Service Module
Implements deterministic byte-level message payload fragmentation into N parts (2 <= N <= 10).
Distributes bytes evenly across N fragments and preserves exact byte order.
Zero AI/ML dependencies - purely deterministic algorithmic logic.
"""

import base64
from typing import List, Dict, Any, Union
from app.validators.fragment_validator import validate_fragment_count
from app.crypto.hashing import sha256_bytes

class FragmentationService:
    """Service for deterministic payload fragmentation."""

    @staticmethod
    def fragment_payload(
        payload: Union[bytes, str],
        fragment_count: int,
        message_uuid: str
    ) -> List[Dict[str, Any]]:
        """
        Divide payload into exactly N ordered fragments (2 <= N <= 10).
        
        Algorithm:
          1. Validate 2 <= N <= 10.
          2. Convert payload to byte representation.
          3. Calculate base chunk size q = L // N and remainder r = L % N.
          4. For i from 1 to N:
             - If i <= r: chunk_size = q + 1
             - Else: chunk_size = q
          5. Slice payload deterministically. If L < N, trailing fragments receive 0 bytes.
          6. Compute SHA-256 checksum and base64 encoding for each fragment.
          7. Return exactly N fragment descriptors.
        """
        is_valid, n, error_msg = validate_fragment_count(fragment_count)
        if not is_valid:
            raise ValueError(f"Invalid fragment count: {error_msg}")

        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        elif isinstance(payload, (bytes, bytearray)):
            payload_bytes = bytes(payload)
        else:
            raise TypeError("Payload must be bytes or string.")

        total_len = len(payload_bytes)
        q = total_len // n
        r = total_len % n

        fragments = []
        offset = 0

        for index in range(1, n + 1):
            # First r fragments get 1 extra byte
            chunk_size = q + 1 if index <= r else q
            chunk_bytes = payload_bytes[offset : offset + chunk_size]
            offset += chunk_size

            chunk_hash = sha256_bytes(chunk_bytes)
            chunk_b64 = base64.b64encode(chunk_bytes).decode("ascii")

            fragments.append({
                "message_uuid": message_uuid,
                "fragment_index": index,
                "total_fragments": n,
                "payload_bytes": chunk_bytes,
                "payload_b64": chunk_b64,
                "payload_hash": chunk_hash,
                "size_bytes": len(chunk_bytes),
            })

        return fragments
