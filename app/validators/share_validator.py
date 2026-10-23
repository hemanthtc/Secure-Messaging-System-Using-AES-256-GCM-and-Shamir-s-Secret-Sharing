"""
Share Validator Module
Validates Shamir's Secret Sharing threshold K and total shares M configuration.
"""

from typing import Tuple, Optional, Any

def validate_sss_parameters(k_threshold: Any, m_total: Any) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
    """
    Validate that:
      - 2 <= K <= M <= 10
      - K and M are strict integers
    Returns (is_valid, k_int, m_int, error_message).
    """
    if k_threshold is None or m_total is None:
        return False, None, None, "Both threshold (K) and total shares (M) are required when Shamir Secret Sharing is enabled."

    if isinstance(k_threshold, bool) or isinstance(m_total, bool):
        return False, None, None, "Threshold and total shares must be integers."

    try:
        k_int = int(k_threshold)
        m_int = int(m_total)
    except (ValueError, TypeError):
        return False, None, None, "Threshold K and total shares M must be valid integers."

    if k_int < 2:
        return False, None, None, f"Key recovery threshold K ({k_int}) must be at least 2."

    if m_int < 2:
        return False, None, None, f"Total key shares M ({m_int}) must be at least 2."

    if m_int > 10:
        return False, None, None, f"Total key shares M ({m_int}) cannot exceed 10."

    if k_int > m_int:
        return False, None, None, f"Threshold K ({k_int}) cannot be greater than total shares M ({m_int})."

    return True, k_int, m_int, None
