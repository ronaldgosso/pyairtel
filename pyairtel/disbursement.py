"""Disbursement API — transfer money to an Airtel Money subscriber."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .exceptions import DisbursementError
from .utils import encrypt_pin, generate_transaction_id, normalise_phone

# ---------------------------------------------------------------------------
# Response dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ValidationResponse:
    """Result of a payee phone number validation check."""

    phone: str
    is_valid: bool
    message: str
    raw: dict[str, Any]


@dataclass
class DisbursementResponse:
    """Result of a disbursement (money transfer) request."""

    transaction_id: str
    status: str
    message: str
    airtel_money_id: str
    raw: dict[str, Any]

    @property
    def is_successful(self) -> bool:
        return self.status.upper() in {"SUCCESS", "200"}


# ---------------------------------------------------------------------------
# Disbursement API client
# ---------------------------------------------------------------------------


class DisbursementAPI:
    """
    Wraps the Airtel Disbursement / Remittance endpoints.

    You do not instantiate this directly — use :class:`pyairtel.AirtelMoney`.
    """

    _VALIDATE_PATH = "/standard/v1/disbursements/wallet-balance/check"
    _TRANSFER_PATH = "/standard/v1/disbursements/"

    def __init__(
        self,
        base_url: str,
        token_manager: Any,
        country: str = "TZ",
        currency: str = "TZS",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_manager = token_manager
        self._country = country
        self._currency = currency

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def validate_payee(self, phone: str) -> ValidationResponse:
        """
        Check whether a phone number is an active Airtel Money account
        that can receive transfers.

        Parameters
        ----------
        phone:
            Payee's phone number (any standard TZ format).

        Returns
        -------
        ValidationResponse
        """
        msisdn = normalise_phone(phone)
        path = f"/standard/v1/disbursements/mobile-money/validity?msisdn={msisdn}&country={self._country}"
        url = f"{self._base_url}{path}"

        try:
            resp = requests.get(url, headers=self._headers(), timeout=30)
        except requests.RequestException as exc:
            raise DisbursementError(f"Network error during validation: {exc}") from exc

        data = resp.json()
        status_block = data.get("status", {})
        success = resp.status_code == 200 and status_block.get("response_code") == "DP00800001006"

        return ValidationResponse(
            phone=msisdn,
            is_valid=success,
            message=status_block.get("message", ""),
            raw=data,
        )

    def transfer(
        self,
        phone: str,
        amount: float,
        pin: str,
        public_key_pem: str,
        payer_first_name: str,
        payer_last_name: str,
        reference: str,
        transaction_id: str | None = None,
    ) -> DisbursementResponse:
        """
        Transfer money from the merchant's Airtel Money wallet to a subscriber.

        Parameters
        ----------
        phone:
            Payee's phone number (any standard TZ format).
        amount:
            Amount in TZS to send.
        pin:
            Your merchant Airtel Money PIN in plain text — it will be
            RSA-encrypted before transmission.
        public_key_pem:
            The RSA public key from your Airtel developer portal
            (*Key Management → RSA Public Key*), in PEM format.
        payer_first_name:
            Merchant account first name.
        payer_last_name:
            Merchant account last name.
        reference:
            Short description / reference for this transfer.
        transaction_id:
            Optional unique ID. Auto-generated if omitted.

        Returns
        -------
        DisbursementResponse

        Raises
        ------
        DisbursementError
            On network failure or non-200 response.
        EncryptionError
            If RSA encryption fails (e.g. bad public key or missing pycryptodome).
        ValidationError
            If the phone number cannot be normalised.
        """
        msisdn = normalise_phone(phone)
        txn_id = transaction_id or generate_transaction_id()
        encrypted_pin = encrypt_pin(pin, public_key_pem)

        payload = {
            "payee": {
                "msisdn": msisdn,
            },
            "reference": reference,
            "pin": encrypted_pin,
            "transaction": {
                "amount": int(amount),
                "id": txn_id,
                "type": "B2C",
            },
        }

        url = f"{self._base_url}{self._TRANSFER_PATH}"

        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        except requests.RequestException as exc:
            raise DisbursementError(f"Network error during transfer: {exc}") from exc

        if resp.status_code != 200:
            raise DisbursementError(f"Disbursement failed [{resp.status_code}]: {resp.text}")

        data = resp.json()
        status_block = data.get("status", {})
        txn_data = data.get("data", {}).get("transaction", {})

        return DisbursementResponse(
            transaction_id=txn_id,
            status=status_block.get("response_code", "UNKNOWN"),
            message=status_block.get("message", ""),
            airtel_money_id=txn_data.get("airtel_money_id", ""),
            raw=data,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "X-Country": self._country,
            "X-Currency": self._currency,
            "Authorization": f"Bearer {self._token_manager.access_token}",
        }
