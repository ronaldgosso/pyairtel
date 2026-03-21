"""Utility helpers for pyairtel: RSA encryption, phone normalisation, ID generation."""

from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime, timezone

from .exceptions import EncryptionError, ValidationError

# ---------------------------------------------------------------------------
# Phone number helpers
# ---------------------------------------------------------------------------


def normalise_phone(phone: str, country_code: str = "255") -> str:
    """
    Normalise a Tanzanian phone number to Airtel's expected format (no leading +).

    Examples
    --------
    >>> normalise_phone("+255681219610")
    '255681219610'
    >>> normalise_phone("0681219610")
    '255681219610'
    >>> normalise_phone("681219610")
    '255681219610'
    """
    phone = re.sub(r"\s+", "", phone)  # strip whitespace

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.startswith("0"):
        phone = country_code + phone[1:]

    if not phone.startswith(country_code):
        phone = country_code + phone

    if not re.fullmatch(r"\d{12}", phone):
        raise ValidationError(f"Phone number '{phone}' is not a valid 12-digit Tanzanian number.")

    return phone


# ---------------------------------------------------------------------------
# Transaction ID generator
# ---------------------------------------------------------------------------


def generate_transaction_id() -> str:
    """Return a unique transaction reference string based on timestamp + uuid4."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    unique = uuid.uuid4().hex[:8].upper()
    return f"TXN-{ts}-{unique}"


# ---------------------------------------------------------------------------
# RSA PIN encryption
# ---------------------------------------------------------------------------


def encrypt_pin(raw_pin: str, public_key_pem: str) -> str:
    """
    RSA-encrypt *raw_pin* with Airtel's public key using PKCS#1 v1.5 padding.

    Parameters
    ----------
    raw_pin:
        The merchant's plain-text Airtel Money PIN (e.g. ``"1234"``).
    public_key_pem:
        The RSA public key in PEM format obtained from the Airtel developer
        portal under *Key Management*.

    Returns
    -------
    str
        Base64-encoded ciphertext ready to embed in the disbursement payload.

    Raises
    ------
    EncryptionError
        If ``pycryptodome`` is not installed or encryption fails for any reason.
    """
    try:
        from Crypto.Cipher import PKCS1_v1_5  # type: ignore[import]
        from Crypto.PublicKey import RSA  # type: ignore[import]
    except ImportError as exc:
        raise EncryptionError(
            "pycryptodome is required for PIN encryption. "
            "Install it with: pip install pycryptodome"
        ) from exc

    try:
        key = RSA.import_key(public_key_pem)
        cipher = PKCS1_v1_5.new(key)
        encrypted_bytes = cipher.encrypt(raw_pin.encode("utf-8"))
        return base64.b64encode(encrypted_bytes).decode("utf-8")
    except Exception as exc:
        raise EncryptionError(f"PIN encryption failed: {exc}") from exc
