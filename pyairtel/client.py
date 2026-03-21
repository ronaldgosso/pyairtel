"""Main AirtelMoney client — the single entry point for pyairtel."""

from __future__ import annotations

from .auth import TokenManager
from .collection import CollectionAPI, CollectionResponse, RefundResponse, TransactionStatusResponse
from .disbursement import DisbursementAPI, DisbursementResponse, ValidationResponse

# Public re-exports so callers can do: from pyairtel import AirtelMoney
__all__ = [
    "AirtelMoney",
    "CollectionResponse",
    "TransactionStatusResponse",
    "RefundResponse",
    "DisbursementResponse",
    "ValidationResponse",
]

# Airtel Open API base URLs
_SANDBOX_URL = "https://openapiuat.airtel.africa"
_PRODUCTION_URL = "https://openapi.airtel.africa"


class AirtelMoney:
    """
    Python client for the Airtel Money Open API (Tanzania).

    Parameters
    ----------
    client_id:
        Your Airtel application Client ID from the developer portal.
    client_secret:
        Your Airtel application Client Secret from the developer portal.
    sandbox:
        If ``True`` (default), requests go to the UAT/sandbox environment.
        Set to ``False`` for live production transactions.
    country:
        ISO country code. Defaults to ``"TZ"`` (Tanzania).
    currency:
        ISO currency code. Defaults to ``"TZS"`` (Tanzanian Shilling).

    Examples
    --------
    **Collect money from a subscriber**

    >>> from pyairtel import AirtelMoney
    >>> airtel = AirtelMoney(client_id="...", client_secret="...", sandbox=True)
    >>> resp = airtel.collect(phone="+255681219610", amount=5000, reference="order-99")
    >>> print(resp.transaction_id, resp.is_initiated)

    **Check collection status**

    >>> status = airtel.get_collection_status(resp.transaction_id)
    >>> print(status.is_successful, status.message)

    **Transfer money to a subscriber**

    >>> d = airtel.transfer(
    ...     phone="+255681219610",
    ...     amount=2000,
    ...     pin="1234",
    ...     public_key_pem=open("airtel_pub.pem").read(),
    ...     payer_first_name="Ronald",
    ...     payer_last_name="Gosso",
    ...     reference="payout-01",
    ... )
    >>> print(d.is_successful, d.airtel_money_id)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = True,
        country: str = "TZ",
        currency: str = "TZS",
    ) -> None:
        base_url = _SANDBOX_URL if sandbox else _PRODUCTION_URL

        self._token_manager = TokenManager(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
        )
        self._collection = CollectionAPI(
            base_url=base_url,
            token_manager=self._token_manager,
            country=country,
            currency=currency,
        )
        self._disbursement = DisbursementAPI(
            base_url=base_url,
            token_manager=self._token_manager,
            country=country,
            currency=currency,
        )

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect(
        self,
        phone: str,
        amount: float,
        reference: str,
        transaction_id: str | None = None,
    ) -> CollectionResponse:
        """
        Send a USSD push payment request to a subscriber.

        The subscriber will be prompted on their phone to enter their
        Airtel Money PIN to authorise the payment.

        Parameters
        ----------
        phone:
            Subscriber's phone number. Accepts ``+255…``, ``0…``, or ``255…``.
        amount:
            Amount to collect in TZS.
        reference:
            Short label for this payment (e.g. ``"invoice-99"``).
        transaction_id:
            Optional unique transaction ID. Auto-generated if omitted.

        Returns
        -------
        CollectionResponse
        """
        return self._collection.collect(
            phone=phone,
            amount=amount,
            reference=reference,
            transaction_id=transaction_id,
        )

    def get_collection_status(self, transaction_id: str) -> TransactionStatusResponse:
        """
        Poll the status of a previously initiated collection.

        Parameters
        ----------
        transaction_id:
            The ID returned (or supplied) when you called :meth:`collect`.

        Returns
        -------
        TransactionStatusResponse
        """
        return self._collection.get_status(transaction_id)

    def refund(self, airtel_money_id: str) -> RefundResponse:
        """
        Refund a completed Airtel Money transaction.

        Parameters
        ----------
        airtel_money_id:
            Airtel's internal reference from a successful collection
            (found in ``TransactionStatusResponse.airtel_money_id``).

        Returns
        -------
        RefundResponse

        Examples
        --------
        >>> status = airtel.get_collection_status(txn_id)
        >>> if status.is_successful:
        ...     refund = airtel.refund(status.airtel_money_id)
        ...     print(refund.is_successful)
        """
        return self._collection.refund(airtel_money_id)

    # ------------------------------------------------------------------
    # Disbursement
    # ------------------------------------------------------------------

    def validate_payee(self, phone: str) -> ValidationResponse:
        """
        Check whether a phone number is registered and can receive money.

        Parameters
        ----------
        phone:
            Payee's phone number.

        Returns
        -------
        ValidationResponse
        """
        return self._disbursement.validate_payee(phone)

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
        Transfer money from the merchant wallet to a subscriber.

        Parameters
        ----------
        phone:
            Payee's phone number.
        amount:
            Amount in TZS to send.
        pin:
            Merchant's plain-text Airtel Money PIN (RSA-encrypted before sending).
        public_key_pem:
            RSA public key from Airtel developer portal (*Key Management*).
        payer_first_name:
            Merchant's first name.
        payer_last_name:
            Merchant's last name.
        reference:
            Short description for this transfer.
        transaction_id:
            Optional unique ID. Auto-generated if omitted.

        Returns
        -------
        DisbursementResponse
        """
        return self._disbursement.transfer(
            phone=phone,
            amount=amount,
            pin=pin,
            public_key_pem=public_key_pem,
            payer_first_name=payer_first_name,
            payer_last_name=payer_last_name,
            reference=reference,
            transaction_id=transaction_id,
        )
