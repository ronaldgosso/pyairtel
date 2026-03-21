# Changelog

All notable changes to `pyairtel` will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2025-03-21

### Added
- OAuth2 authentication with automatic token refresh (60s before expiry)
- Collection API — USSD push payments to Airtel Money subscribers
- Transaction status polling with typed responses (`is_successful`, `is_pending`, `is_failed`)
- Disbursement API — B2C transfers with RSA PIN encryption via `pycryptodome`
- Refund API — reverse completed collections using `airtel_money_id`
- Phone number normalisation for Tanzania (`+255`, `0`, `255` formats)
- ESB error code decoding — all 9 Airtel Tanzania production codes mapped to human-readable messages
- `CollectionError.esb_code` and `CollectionError.esb_message` attributes on every failed request
- Sandbox and production environment support via `sandbox=True/False`
- 25 unit tests, zero real network calls (fully mocked with `responses`)
- CI/CD via GitHub Actions — lint, type-check, and test matrix on Python 3.9–3.12
- Auto-publish to PyPI on version tags via trusted publishing (OIDC)

---

[0.1.0]: https://github.com/ronaldgosso/pyairtel/releases/tag/v0.1.0