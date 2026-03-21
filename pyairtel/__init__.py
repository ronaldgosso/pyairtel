"""
pyairtel — Python client for Airtel Money Tanzania.

Quick start
-----------
>>> from pyairtel import AirtelMoney
>>> airtel = AirtelMoney(client_id="...", client_secret="...", sandbox=True)
>>> resp = airtel.collect(phone="+255681219610", amount=5000, reference="order-1")
>>> print(resp.transaction_id)
"""

from .client import AirtelMoney
from .collection import CollectionResponse, RefundResponse, TransactionStatusResponse
from .disbursement import DisbursementResponse, ValidationResponse
from .exceptions import (
    AirtelError,
    AuthenticationError,
    CollectionError,
    DisbursementError,
    EncryptionError,
    ValidationError,
    decode_esb_error,
)

__version__ = "0.1.0"
__author__ = "Ronald Isack Gosso"
__email__ = "ronaldgosso@gmail.com"

__all__ = [
    "AirtelMoney",
    # Responses
    "CollectionResponse",
    "TransactionStatusResponse",
    "RefundResponse",
    "DisbursementResponse",
    "ValidationResponse",
    # Exceptions
    "AirtelError",
    "AuthenticationError",
    "CollectionError",
    "DisbursementError",
    "EncryptionError",
    "ValidationError",
    # Utilities
    "decode_esb_error",
    # Metadata
    "__version__",
]
