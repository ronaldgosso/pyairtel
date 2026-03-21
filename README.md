# pyairtel

[![PyPI version](https://img.shields.io/pypi/v/pyairtel?color=green)](https://pypi.org/project/pyairtel/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyairtel)](https://pypi.org/project/pyairtel/)
[![CI](https://github.com/ronaldgosso/pyairtel/actions/workflows/ci.yml/badge.svg)](https://github.com/ronaldgosso/pyairtel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Python client for **Airtel Money Tanzania** — Collection & Disbursement APIs.

---

## Features

- 🔐 **OAuth2 authentication** with automatic token refresh
- 📲 **Collection** — USSD push payments (request money from subscribers)
- ✅ **Transaction status** polling
- 💸 **Disbursement** — transfer money to Airtel Money wallets
- 🔒 **RSA PIN encryption** for disbursement security
- 📞 **Phone number normalisation** (handles `+255…`, `0…`, `255…` formats)
- 🧪 **Sandbox & Production** environments

---

## Installation

```bash
pip install pyairtel
```

For disbursement with PIN encryption, install the encryption extra:

```bash
pip install "pyairtel[encryption]"
```

---

## Quick Start

### 1. Get credentials

Create an account at [developers.airtel.co.tz](https://developers.airtel.co.tz/user/signup), create an application, and add **Collection** and **Disbursement** APIs. Copy your `client_id` and `client_secret` from **Key Management**.

### 2. Collect money from a subscriber

```python
from pyairtel import AirtelMoney

airtel = AirtelMoney(
    client_id="your-client-id",
    client_secret="your-client-secret",
    sandbox=True,          # set False for production
)

response = airtel.collect(
    phone="+255681219610",
    amount=5000,
    reference="invoice-42",
)

print(response.transaction_id)  # TXN-20240101120000123456-AB12CD34
print(response.is_initiated)    # True
```

### 3. Check transaction status

```python
import time

time.sleep(15)  # give the subscriber time to approve

status = airtel.get_collection_status(response.transaction_id)

if status.is_successful:
    print("Payment confirmed!", status.airtel_money_id)
elif status.is_pending:
    print("Still waiting for subscriber to approve...")
elif status.is_failed:
    print("Payment failed:", status.message)
```

### 4. Transfer money to a subscriber (Disbursement)

```python
# First validate the payee
check = airtel.validate_payee("+255681219610")
if not check.is_valid:
    print("Payee cannot receive money:", check.message)
else:
    result = airtel.transfer(
        phone="+255681219610",
        amount=2000,
        pin="1234",                              # your merchant PIN
        public_key_pem=open("airtel_pub.pem").read(),  # from Key Management
        payer_first_name="Ronald",
        payer_last_name="Gosso",
        reference="payout-001",
    )
    print(result.is_successful, result.airtel_money_id)
```

---

## Environment

| Parameter | Sandbox | Production |
|-----------|---------|------------|
| `sandbox` | `True` | `False` |
| Base URL | `https://openapiuat.airtel.africa` | `https://openapi.airtel.africa` |

---

## Error Handling

```python
from pyairtel import AirtelMoney
from pyairtel.exceptions import AuthenticationError, CollectionError, EncryptionError

try:
    resp = airtel.collect(phone="+255681219610", amount=1000, reference="ref-1")
except AuthenticationError as e:
    print("Bad credentials or token expired:", e)
except CollectionError as e:
    print("Collection failed:", e)
```

| Exception | When raised |
|-----------|-------------|
| `AuthenticationError` | Token acquisition fails (bad credentials, network) |
| `CollectionError` | USSD push or status check fails |
| `DisbursementError` | Transfer or payee validation fails |
| `EncryptionError` | RSA PIN encryption fails (e.g. missing `pycryptodome`) |
| `ValidationError` | Invalid phone number format |

---

## License

MIT © [Ronald Isack Gosso](https://github.com/ronaldgosso)
