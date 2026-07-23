"""RED tests for CORS credentialed cross-origin requests (tenancy-isolation
spec — "Cross-Origin Credentialed Requests Restricted to Trusted Origins").
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_allowlisted_origin_gets_credentialed_cors_headers():
    client = APIClient()
    response = client.get(
        "/api/auth/csrf/",
        HTTP_ORIGIN="http://localhost:3000",
    )
    assert response["Access-Control-Allow-Credentials"] == "true"
    assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_non_allowlisted_origin_gets_no_credentialed_cors_headers():
    client = APIClient()
    response = client.get(
        "/api/auth/csrf/",
        HTTP_ORIGIN="http://evil.example.com",
    )
    assert "Access-Control-Allow-Credentials" not in response
    assert "Access-Control-Allow-Origin" not in response
