"""Custom exceptions for pyairtel."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# ESB error code table — sourced from real Airtel Tanzania production traffic
# ---------------------------------------------------------------------------

_ESB_CODES: dict[str, str] = {
    "ESB000001": "Transaction failed — general error. Check your credentials and try again.",
    "ESB000004": "Service unavailable. Airtel Money service is temporarily down.",
    "ESB000008": "Invalid transaction. The request parameters are incorrect.",
    "ESB000011": "Subscriber not found. The phone number is not registered on Airtel Money.",
    "ESB000014": "Insufficient funds. The subscriber's Airtel Money balance is too low.",
    "ESB000033": "Transaction limit exceeded. The amount is above the subscriber's transaction limit.",
    "ESB000036": "Daily limit exceeded. The subscriber has reached their daily transaction limit.",
    "ESB000039": "Transaction timed out. The subscriber did not respond to the USSD prompt in time.",
    "ESB000041": "Subscriber PIN locked. Too many incorrect PIN attempts.",
    "ESB000045": "Duplicate transaction. A transaction with this ID was already processed.",
}


def decode_esb_error(code: str | None) -> str:
    """
    Translate an Airtel ESB error code into a human-readable message.

    Parameters
    ----------
    code:
        The ESB error code string (e.g. ``"ESB000014"``).

    Returns
    -------
    str
        A human-readable description of the error, or a generic fallback
        if the code is not recognised.

    Examples
    --------
    >>> decode_esb_error("ESB000014")
    "Insufficient funds. The subscriber's Airtel Money balance is too low."
    >>> decode_esb_error("ESB999999")
    "Unknown error (ESB999999). Check the raw response for details."
    """
    if not code:
        return "Unknown error — no error code provided."
    return _ESB_CODES.get(code, f"Unknown error ({code}). Check the raw response for details.")


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------


class AirtelError(Exception):
    """Base exception for all pyairtel errors."""

    pass


class AuthenticationError(AirtelError):
    """Raised when OAuth2 token acquisition fails."""

    pass


class CollectionError(AirtelError):
    """
    Raised when a collection (USSD push) or refund request fails.

    Attributes
    ----------
    esb_code:
        The raw Airtel ESB error code if one was returned (e.g. ``"ESB000014"``).
    esb_message:
        Human-readable translation of ``esb_code`` via :func:`decode_esb_error`.
    """

    def __init__(self, message: str, esb_code: str | None = None) -> None:
        self.esb_code = esb_code
        self.esb_message = decode_esb_error(esb_code) if esb_code else None
        full = f"{message} | ESB: {esb_code} — {self.esb_message}" if esb_code else message
        super().__init__(full)


class DisbursementError(AirtelError):
    """Raised when a disbursement (transfer) request fails."""

    pass


class ValidationError(AirtelError):
    """Raised when input validation fails."""

    pass


class EncryptionError(AirtelError):
    """Raised when RSA PIN encryption fails."""

    pass
