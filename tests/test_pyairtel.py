"""Unit tests for pyairtel — no real network calls, everything mocked."""

from __future__ import annotations

import pytest
import responses as resp_mock

from pyairtel import AirtelMoney, decode_esb_error
from pyairtel.exceptions import AuthenticationError, CollectionError, ValidationError
from pyairtel.utils import generate_transaction_id, normalise_phone

# ---------------------------------------------------------------------------
# Utils tests
# ---------------------------------------------------------------------------


class TestNormalisePhone:
    def test_plus_prefix(self):
        assert normalise_phone("+255754123456") == "255754123456"

    def test_zero_prefix(self):
        assert normalise_phone("0754123456") == "255754123456"

    def test_already_correct(self):
        assert normalise_phone("255754123456") == "255754123456"

    def test_bare_number(self):
        assert normalise_phone("754123456") == "255754123456"

    def test_with_spaces(self):
        assert normalise_phone("+255 754 123 456") == "255754123456"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            normalise_phone("123")


class TestGenerateTransactionId:
    def test_format(self):
        txn_id = generate_transaction_id()
        assert txn_id.startswith("TXN-")
        assert len(txn_id) > 10

    def test_uniqueness(self):
        ids = {generate_transaction_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# ESB error code tests
# ---------------------------------------------------------------------------


class TestDecodeEsbError:
    def test_known_code_insufficient_funds(self):
        msg = decode_esb_error("ESB000014")
        assert "Insufficient funds" in msg

    def test_known_code_subscriber_not_found(self):
        msg = decode_esb_error("ESB000011")
        assert "not registered" in msg

    def test_known_code_timed_out(self):
        msg = decode_esb_error("ESB000039")
        assert "timed out" in msg

    def test_known_code_duplicate(self):
        msg = decode_esb_error("ESB000045")
        assert "Duplicate" in msg

    def test_unknown_code_returns_fallback(self):
        msg = decode_esb_error("ESB999999")
        assert "ESB999999" in msg

    def test_none_returns_fallback(self):
        msg = decode_esb_error(None)
        assert "Unknown" in msg

    def test_collection_error_carries_esb_code(self):
        err = CollectionError("Payment failed", esb_code="ESB000014")
        assert err.esb_code == "ESB000014"
        assert "Insufficient funds" in err.esb_message  # type: ignore[operator]
        assert "ESB000014" in str(err)


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestTokenManager:
    @resp_mock.activate
    def test_fetches_token_on_first_access(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/auth/oauth2/token",
            json={"access_token": "test-token-abc", "expires_in": 7200},
            status=200,
        )
        airtel = AirtelMoney(client_id="id", client_secret="secret", sandbox=True)
        token = airtel._token_manager.access_token
        assert token == "test-token-abc"

    @resp_mock.activate
    def test_raises_on_bad_credentials(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/auth/oauth2/token",
            json={"error": "invalid_client"},
            status=401,
        )
        airtel = AirtelMoney(client_id="bad", client_secret="creds", sandbox=True)
        with pytest.raises(AuthenticationError):
            _ = airtel._token_manager.access_token


# ---------------------------------------------------------------------------
# Collection tests
# ---------------------------------------------------------------------------


class TestCollection:
    def _make_airtel(self, token: str = "tok") -> AirtelMoney:
        airtel = AirtelMoney(client_id="id", client_secret="secret", sandbox=True)
        airtel._token_manager._access_token = token
        airtel._token_manager._expires_at = 9_999_999_999
        return airtel

    @resp_mock.activate
    def test_collect_success(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/merchant/v1/payments/",
            json={"status": {"response_code": "DP00800001001", "message": "Accepted"}},
            status=200,
        )
        airtel = self._make_airtel()
        result = airtel.collect(phone="+255754123456", amount=5000, reference="test-ref")
        assert result.is_initiated
        assert result.transaction_id.startswith("TXN-")

    @resp_mock.activate
    def test_collect_network_error(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/merchant/v1/payments/",
            body=Exception("timeout"),
        )
        airtel = self._make_airtel()
        with pytest.raises(CollectionError):
            airtel.collect(phone="+255754123456", amount=5000, reference="ref")

    @resp_mock.activate
    def test_collect_esb_error_surfaces_code(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/merchant/v1/payments/",
            json={"status": {"response_code": "ESB000014", "message": "Insufficient balance"}},
            status=400,
        )
        airtel = self._make_airtel()
        with pytest.raises(CollectionError) as exc_info:
            airtel.collect(phone="+255754123456", amount=5000, reference="ref")
        assert exc_info.value.esb_code == "ESB000014"
        assert "Insufficient funds" in str(exc_info.value)

    @resp_mock.activate
    def test_get_collection_status_successful(self):
        txn_id = "TXN-TEST-001"
        resp_mock.add(
            resp_mock.GET,
            f"https://openapiuat.airtel.africa/standard/v1/payments/{txn_id}",
            json={
                "data": {
                    "transaction": {
                        "status": "TS",
                        "message": "Transaction Successful",
                        "airtel_money_id": "CI240101.1234.A00001",
                    }
                }
            },
            status=200,
        )
        airtel = self._make_airtel()
        status = airtel.get_collection_status(txn_id)
        assert status.is_successful
        assert not status.is_pending
        assert not status.is_failed
        assert status.airtel_money_id == "CI240101.1234.A00001"

    @resp_mock.activate
    def test_get_collection_status_pending(self):
        txn_id = "TXN-TEST-002"
        resp_mock.add(
            resp_mock.GET,
            f"https://openapiuat.airtel.africa/standard/v1/payments/{txn_id}",
            json={
                "data": {
                    "transaction": {
                        "status": "TIP",
                        "message": "In Progress",
                        "airtel_money_id": "",
                    }
                }
            },
            status=200,
        )
        airtel = self._make_airtel()
        status = airtel.get_collection_status(txn_id)
        assert status.is_pending
        assert not status.is_successful

    @resp_mock.activate
    def test_get_collection_status_failed(self):
        txn_id = "TXN-TEST-003"
        resp_mock.add(
            resp_mock.GET,
            f"https://openapiuat.airtel.africa/standard/v1/payments/{txn_id}",
            json={
                "data": {
                    "transaction": {
                        "status": "TF",
                        "message": "Failed",
                        "airtel_money_id": "",
                    }
                }
            },
            status=200,
        )
        airtel = self._make_airtel()
        status = airtel.get_collection_status(txn_id)
        assert status.is_failed
        assert not status.is_successful


# ---------------------------------------------------------------------------
# Refund tests
# ---------------------------------------------------------------------------


class TestRefund:
    def _make_airtel(self, token: str = "tok") -> AirtelMoney:
        airtel = AirtelMoney(client_id="id", client_secret="secret", sandbox=True)
        airtel._token_manager._access_token = token
        airtel._token_manager._expires_at = 9_999_999_999
        return airtel

    @resp_mock.activate
    def test_refund_success(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/standard/v1/payments/refund",
            json={"status": {"response_code": "DP00800001001", "message": "Refund initiated"}},
            status=200,
        )
        airtel = self._make_airtel()
        result = airtel.refund("CI240101.1234.A00001")
        assert result.is_successful
        assert result.airtel_money_id == "CI240101.1234.A00001"
        assert result.message == "Refund initiated"

    @resp_mock.activate
    def test_refund_failure_carries_esb_code(self):
        resp_mock.add(
            resp_mock.POST,
            "https://openapiuat.airtel.africa/standard/v1/payments/refund",
            json={"status": {"response_code": "ESB000001", "message": "General error"}},
            status=400,
        )
        airtel = self._make_airtel()
        with pytest.raises(CollectionError) as exc_info:
            airtel.refund("CI240101.9999.X00001")
        assert exc_info.value.esb_code == "ESB000001"
        assert "General error" in str(exc_info.value)
