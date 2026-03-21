"""Collection API — request payments, check status, and refund transactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .exceptions import CollectionError
from .utils import generate_transaction_id, normalise_phone

# ---------------------------------------------------------------------------
# Response dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CollectionResponse:
    """Result of a collection (USSD push) request."""

    transaction_id: str
    """The transaction ID you supplied (or auto-generated)."""
    status: str
    """Raw status string from Airtel (e.g. ``'SUCCESS'``, ``'DP_INITIATED'``)."""
    message: str
    """Human-readable message from Airtel."""
    raw: dict[str, Any]
    """The complete raw JSON response."""

    @property
    def is_initiated(self) -> bool:
        """``True`` if the USSD push was successfully sent to the subscriber."""
        # DP00800001001 = success/initiated per Airtel Open API response codes
        return self.status.upper() in {
            "SUCCESS",
            "DP_INITIATED",
            "DP00800001001",
            "200",
        }


@dataclass
class TransactionStatusResponse:
    """Result of a transaction status enquiry."""

    transaction_id: str
    status: str
    """
    Known values:

    * ``TS``  — Transaction Successful
    * ``TIP`` — Transaction In Progress
    * ``TA``  — Transaction Ambiguous
    * ``TF``  — Transaction Failed
    """
    message: str
    airtel_money_id: str
    """Airtel's own internal reference number."""
    raw: dict[str, Any]

    @property
    def is_successful(self) -> bool:
        return self.status.upper() == "TS"

    @property
    def is_pending(self) -> bool:
        return self.status.upper() in {"TIP", "DP_INITIATED"}

    @property
    def is_failed(self) -> bool:
        return self.status.upper() in {"TF", "TA"}


@dataclass
class RefundResponse:
    """Result of a refund request."""

    airtel_money_id: str
    """The Airtel internal ID of the original transaction being refunded."""
    status: str
    """Raw status from Airtel."""
    message: str
    raw: dict[str, Any]

    @property
    def is_successful(self) -> bool:
        return self.status.upper() in {"SUCCESS", "DP00800001001", "200"}


# ---------------------------------------------------------------------------
# Collection API client
# ---------------------------------------------------------------------------


class CollectionAPI:
    """
    Wraps the Airtel Collection endpoints.

    You do not instantiate this directly — use :class:`pyairtel.AirtelMoney`.
    """

    _COLLECT_PATH = "/merchant/v1/payments/"
    _STATUS_PATH = "/standard/v1/payments/{transaction_id}"
    _REFUND_PATH = "/standard/v1/payments/refund"

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

    def collect(
        self,
        phone: str,
        amount: float,
        reference: str,
        transaction_id: str | None = None,
    ) -> CollectionResponse:
        """
        Initiate a USSD push payment request.

        The subscriber will receive a prompt on their phone asking them to
        authorise the payment by entering their Airtel Money PIN.

        Parameters
        ----------
        phone:
            Subscriber's phone number. Accepts ``+255…``, ``0…``, or ``255…``
            formats — normalised automatically.
        amount:
            Amount to collect in TZS (no decimals for whole amounts).
        reference:
            A short human-readable label for this payment (e.g. ``"invoice-42"``).
        transaction_id:
            Optional unique ID. Auto-generated if omitted.

        Returns
        -------
        CollectionResponse

        Raises
        ------
        CollectionError
            On network failure or a non-200 response from Airtel.
        ValidationError
            If the phone number cannot be normalised.
        """
        msisdn = normalise_phone(phone)
        txn_id = transaction_id or generate_transaction_id()

        payload = {
            "reference": reference,
            "subscriber": {
                "country": self._country,
                "currency": self._currency,
                "msisdn": int(msisdn),
            },
            "transaction": {
                "amount": int(amount),
                "country": self._country,
                "currency": self._currency,
                "id": txn_id,
            },
        }

        data = self._post(self._COLLECT_PATH, payload)
        status_block = data.get("status", {})

        return CollectionResponse(
            transaction_id=txn_id,
            status=status_block.get("response_code", "UNKNOWN"),
            message=status_block.get("message", ""),
            raw=data,
        )

    def get_status(self, transaction_id: str) -> TransactionStatusResponse:
        """
        Check the status of a previously initiated collection.

        Parameters
        ----------
        transaction_id:
            The same ID you passed (or received) when calling :meth:`collect`.

        Returns
        -------
        TransactionStatusResponse
        """
        path = self._STATUS_PATH.format(transaction_id=transaction_id)
        data = self._get(path)

        txn = data.get("data", {}).get("transaction", {})

        return TransactionStatusResponse(
            transaction_id=transaction_id,
            status=txn.get("status", "UNKNOWN"),
            message=txn.get("message", ""),
            airtel_money_id=txn.get("airtel_money_id", ""),
            raw=data,
        )

    def refund(self, airtel_money_id: str) -> RefundResponse:
        """
        Refund a completed Airtel Money transaction.

        Use the ``airtel_money_id`` returned in :class:`TransactionStatusResponse`
        after a successful collection — **not** the transaction ID you generated.

        Parameters
        ----------
        airtel_money_id:
            Airtel's internal transaction reference (e.g. ``"CI240101.1234.A00001"``).
            This is found in ``TransactionStatusResponse.airtel_money_id``.

        Returns
        -------
        RefundResponse

        Raises
        ------
        CollectionError
            On network failure or non-200 response from Airtel.

        Examples
        --------
        >>> status = airtel.get_collection_status(txn_id)
        >>> if status.is_successful:
        ...     refund = airtel.refund(status.airtel_money_id)
        ...     print(refund.is_successful)
        """
        payload = {"transaction": {"airtel_money_id": airtel_money_id}}
        data = self._post(self._REFUND_PATH, payload)
        status_block = data.get("status", {})

        return RefundResponse(
            airtel_money_id=airtel_money_id,
            status=status_block.get("response_code", "UNKNOWN"),
            message=status_block.get("message", ""),
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

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        except Exception as exc:
            raise CollectionError(f"Network error: {exc}") from exc

        if resp.status_code != 200:
            # Try to extract ESB error code from response body
            esb_code: str | None = None
            try:
                body = resp.json()
                esb_code = body.get("status", {}).get("response_code") or body.get("error", {}).get(
                    "code"
                )
            except Exception:
                pass
            raise CollectionError(
                f"Request failed [{resp.status_code}]: {resp.text}",
                esb_code=esb_code,
            )
        result: dict[str, Any] = resp.json()
        return result

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=30)
        except Exception as exc:
            raise CollectionError(f"Network error: {exc}") from exc

        if resp.status_code != 200:
            raise CollectionError(f"Status check failed [{resp.status_code}]: {resp.text}")
        result: dict[str, Any] = resp.json()
        return result
