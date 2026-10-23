"""
Message Reassembly Service Module
Implements deterministic reassembly of fragmented payloads.
Validates indexes, ignores duplicate arrivals, detects missing fragments,
sorts by index, concatenates payloads, and validates full integrity.
Zero AI/ML dependencies - deterministic algorithms and cryptographic verification only.
"""

import base64
from typing import List, Dict, Any, Optional, Tuple
from app.crypto.hashing import sha256_bytes

class ReassemblyService:
    """Service for validating and reassembling fragmented payloads."""

    @staticmethod
    def reassemble_fragments(
        fragments: List[Dict[str, Any]],
        expected_total: Optional[int] = None,
        expected_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attempt reassembly of message fragments.
        
        Returns a status dictionary:
        {
            "is_complete": bool,
            "status": "COMPLETE" | "WAITING_FOR_MISSING_FRAGMENTS" | "ERROR",
            "received_count": int,
            "total_fragments": int,
            "missing_indexes": List[int],
            "reassembled_bytes": Optional[bytes],
            "error_message": Optional[str]
        }
        """
        if not fragments:
            return {
                "is_complete": False,
                "status": "WAITING_FOR_MISSING_FRAGMENTS",
                "received_count": 0,
                "total_fragments": expected_total or 0,
                "missing_indexes": list(range(1, (expected_total or 0) + 1)),
                "reassembled_bytes": None,
                "error_message": "No fragments received."
            }

        # 1. Verify consistent message_uuid and total_fragments
        first_msg_id = fragments[0].get("message_uuid")
        first_total = fragments[0].get("total_fragments")

        if expected_total is not None and first_total != expected_total:
            return {
                "is_complete": False,
                "status": "ERROR",
                "received_count": len(fragments),
                "total_fragments": expected_total,
                "missing_indexes": [],
                "reassembled_bytes": None,
                "error_message": f"Conflicting total fragments metadata: expected {expected_total}, got {first_total}."
            }

        total_n = expected_total or first_total

        # 2. Process and deduplicate fragments by index
        unique_by_index = {}
        for frag in fragments:
            msg_id = frag.get("message_uuid")
            if msg_id != first_msg_id:
                return {
                    "is_complete": False,
                    "status": "ERROR",
                    "received_count": len(unique_by_index),
                    "total_fragments": total_n,
                    "missing_indexes": [],
                    "reassembled_bytes": None,
                    "error_message": f"Cross-message fragment rejection: fragment belongs to message '{msg_id}', not '{first_msg_id}'."
                }

            frag_total = frag.get("total_fragments")
            if frag_total != total_n:
                return {
                    "is_complete": False,
                    "status": "ERROR",
                    "received_count": len(unique_by_index),
                    "total_fragments": total_n,
                    "missing_indexes": [],
                    "reassembled_bytes": None,
                    "error_message": f"Conflicting total fragment count {frag_total} in fragment {frag.get('fragment_index')}."
                }

            idx = frag.get("fragment_index")
            if not isinstance(idx, int) or idx < 1 or idx > total_n:
                return {
                    "is_complete": False,
                    "status": "ERROR",
                    "received_count": len(unique_by_index),
                    "total_fragments": total_n,
                    "missing_indexes": [],
                    "reassembled_bytes": None,
                    "error_message": f"Invalid fragment index {idx} for total count {total_n}."
                }

            # Verify individual fragment checksum
            payload = frag.get("payload_bytes")
            if payload is None:
                payload_b64 = frag.get("payload") or frag.get("payload_b64")
                if payload_b64 is not None:
                    payload = base64.b64decode(payload_b64)
                else:
                    payload = b""

            expected_frag_hash = frag.get("payload_hash")
            if expected_frag_hash and sha256_bytes(payload).lower() != expected_frag_hash.lower():
                return {
                    "is_complete": False,
                    "status": "ERROR",
                    "received_count": len(unique_by_index),
                    "total_fragments": total_n,
                    "missing_indexes": [],
                    "reassembled_bytes": None,
                    "error_message": f"Fragment {idx} failed SHA-256 integrity check."
                }

            # Ignore or reject duplicates: keep first valid
            if idx not in unique_by_index:
                unique_by_index[idx] = payload

        # 3. Detect missing indexes
        received_count = len(unique_by_index)
        all_expected_indexes = set(range(1, total_n + 1))
        missing_indexes = sorted(list(all_expected_indexes - set(unique_by_index.keys())))

        if missing_indexes:
            return {
                "is_complete": False,
                "status": "WAITING_FOR_MISSING_FRAGMENTS",
                "received_count": received_count,
                "total_fragments": total_n,
                "missing_indexes": missing_indexes,
                "reassembled_bytes": None,
                "error_message": f"Waiting for missing fragments: received {received_count}/{total_n}."
            }

        # 4. Sort fragments by index 1 .. N and concatenate
        assembled_chunks = [unique_by_index[i] for i in range(1, total_n + 1)]
        reassembled_bytes = b"".join(assembled_chunks)

        # 5. Verify full ciphertext integrity if expected hash provided
        if expected_hash:
            computed_hash = sha256_bytes(reassembled_bytes)
            if computed_hash.lower() != expected_hash.lower():
                return {
                    "is_complete": False,
                    "status": "ERROR",
                    "received_count": received_count,
                    "total_fragments": total_n,
                    "missing_indexes": [],
                    "reassembled_bytes": None,
                    "error_message": "Reassembled payload hash mismatch: full payload integrity check failed."
                }

        return {
            "is_complete": True,
            "status": "COMPLETE",
            "received_count": total_n,
            "total_fragments": total_n,
            "missing_indexes": [],
            "reassembled_bytes": reassembled_bytes,
            "error_message": None
        }
