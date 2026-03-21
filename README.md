# pyairtel

![image](./pyairtel.png)

[![PyPI version](https://img.shields.io/pypi/v/pyairtel?color=green)](https://pypi.org/project/pyairtel/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyairtel)](https://pypi.org/project/pyairtel/)
[![CI](https://github.com/ronaldgosso/pyairtel/actions/workflows/ci.yml/badge.svg)](https://github.com/ronaldgosso/pyairtel/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Python client for **Airtel Money Tanzania** — Collection & Disbursement APIs.

📖 **[Full documentation & examples → ronaldgosso.github.io/pyairtel](https://ronaldgosso.github.io/pyairtel)**

---

## Features

- 🔐 **OAuth2 authentication** with automatic token refresh
- 📲 **Collection** — USSD push payments (request money from subscribers)
- ✅ **Transaction status** polling
- 💸 **Disbursement** — transfer money to Airtel Money wallets
- ↩️ **Refunds** — reverse completed transactions by `airtel_money_id`
- 🔒 **RSA PIN encryption** for disbursement security
- 📞 **Phone number normalisation** (handles `+255…`, `0…`, `255…` formats)
- ⚠️ **ESB error decoding** — all 9 Airtel Tanzania error codes mapped to human-readable messages
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
from dotenv import load_dotenv
import os
from pyairtel import AirtelMoney

load_dotenv()

airtel = AirtelMoney(
    client_id=os.environ["AIRTEL_CLIENT_ID"],
    client_secret=os.environ["AIRTEL_CLIENT_SECRET"],
    sandbox=os.getenv("AIRTEL_SANDBOX", "true").lower() == "true",       # set False for production
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

### 5. Refund a transaction

```python
# Use airtel_money_id from a successful collection status
status = airtel.get_collection_status(transaction_id)

if status.is_successful:
    refund = airtel.refund(status.airtel_money_id)
    print(refund.is_successful, refund.message)
```

---

## Environment

| Parameter | Sandbox | Production |
|-----------|---------|------------|
| `sandbox` | `True` | `False` |
| Base URL | `https://openapiuat.airtel.africa` | `https://openapi.airtel.africa` |

---

## Credentials & Environment Variables

Never hardcode credentials in your code. Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

`.env`:
```bash
AIRTEL_CLIENT_ID=your-client-id-here
AIRTEL_CLIENT_SECRET=your-client-secret-here
AIRTEL_SANDBOX=true
AIRTEL_PUBLIC_KEY_PATH=airtel_pub.pem   # disbursement only
```

Then load it in your project:
```python
from dotenv import load_dotenv 
import os
from pyairtel import AirtelMoney

load_dotenv()

airtel = AirtelMoney(
    client_id=os.environ["AIRTEL_CLIENT_ID"],
    client_secret=os.environ["AIRTEL_CLIENT_SECRET"],
    sandbox=os.getenv("AIRTEL_SANDBOX", "true").lower() == "true",
)
```

> ⚠️ `.env` and `*.pem` are in `.gitignore` — never commit them.

## Error Handling

```python
from pyairtel import AirtelMoney, decode_esb_error
from pyairtel.exceptions import AuthenticationError, CollectionError, EncryptionError

try:
    resp = airtel.collect(phone="+255681219610", amount=1000, reference="ref-1")
except AuthenticationError as e:
    print("Bad credentials or token expired:", e)
except CollectionError as e:
    print("Collection failed:", e)
    print("ESB code:", e.esb_code)      # e.g. "ESB000014"
    print("Reason:",   e.esb_message)   # "Insufficient funds..."

# Decode any ESB code manually
print(decode_esb_error("ESB000039"))
# → "Transaction timed out. The subscriber did not respond to the USSD prompt in time."
```

| Exception | When raised |
|-----------|-------------|
| `AuthenticationError` | Token acquisition fails (bad credentials, network) |
| `CollectionError` | USSD push, status check, or refund fails — includes `.esb_code` and `.esb_message` |
| `DisbursementError` | Transfer or payee validation fails |
| `EncryptionError` | RSA PIN encryption fails (e.g. missing `pycryptodome`) |
| `ValidationError` | Invalid phone number format |

### Airtel Tanzania ESB Error Codes

| Code | Meaning |
|------|---------|
| `ESB000001` | General error — check credentials and try again |
| `ESB000004` | Service unavailable — Airtel Money is temporarily down |
| `ESB000008` | Invalid transaction — request parameters are incorrect |
| `ESB000011` | Subscriber not found — number not registered on Airtel Money |
| `ESB000014` | Insufficient funds — subscriber balance too low |
| `ESB000033` | Transaction limit exceeded — amount above subscriber's limit |
| `ESB000036` | Daily limit exceeded — subscriber has hit their daily cap |
| `ESB000039` | Transaction timed out — subscriber didn't respond to USSD prompt |
| `ESB000041` | PIN locked — too many incorrect PIN attempts |
| `ESB000045` | Duplicate transaction — this ID was already processed |

---

## Local Development

Follow these steps to run `pyairtel` locally, run tests, and contribute.

### 1. Clone the repository

```bash
git clone https://github.com/ronaldgosso/pyairtel.git
cd pyairtel
```

### 2. Create and activate a virtual environment

```bash
# Create venv
python -m venv venv

# Activate — Linux / Mac
source venv/bin/activate

# Activate — Windows
venv\Scripts\activate

# Confirm — should show the venv path
which python
```

### 3. Install the package and dev dependencies

```bash
pip install -e ".[dev]"

# Also install encryption support for disbursement tests
pip install -e ".[dev,encryption]"

# install from requirements.txt
pip install -r requirements.txt
```

### 4. Fix lint errors automatically

```bash
# Auto-fix ruff issues (import order, trailing whitespace, deprecated types)
ruff check pyairtel tests --fix --unsafe-fixes

# Format with black
black pyairtel tests
```

### 5. Verify the full quality gate

```bash
# Linting — should print: All checks passed!
ruff check pyairtel tests

# Formatting — should print: X files would be left unchanged.
black --check pyairtel tests

# Type checking — should print: Success: no issues found in 7 source files
mypy pyairtel
```

### 6. Run the test suite

```bash
# Run all 25 tests with verbose output
pytest tests/ -v

# Run a specific test class
pytest tests/ -v -k "TestCollection"

# Run a single test by name
pytest tests/ -v -k "test_collect_success"
```

### 7. Deactivate the venv when done

```bash
deactivate
```

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository on GitHub
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Make your changes — all new code must include tests
4. Run the full quality gate (steps 4–6 above) and ensure everything passes
5. Commit with a descriptive message: `git commit -m "feat: add your feature"`
6. Push and open a Pull Request against `main`

Please keep PRs focused — one feature or fix per PR. If you're unsure whether something is in scope, open an issue first.

---

## License

MIT © [Ronald Isack Gosso](https://github.com/ronaldgosso)