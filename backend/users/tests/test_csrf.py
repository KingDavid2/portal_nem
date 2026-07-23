"""RED tests for the CSRF-bootstrap endpoint (identity-auth spec —
"CSRF-Bootstrap Path Sets the CSRF Cookie").
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_csrf_bootstrap_sets_non_httponly_csrftoken_cookie():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/auth/csrf/")

    assert response.status_code == 200
    csrf_cookie = response.cookies.get("csrftoken")
    assert csrf_cookie is not None
    assert not csrf_cookie["httponly"]


def test_bootstrapped_token_is_accepted_on_a_subsequent_write():
    client = APIClient(enforce_csrf_checks=True)
    bootstrap_response = client.get("/api/auth/csrf/")
    csrf_token = bootstrap_response.cookies["csrftoken"].value

    # The bootstrap endpoint itself is GET-only; POSTing to it with the
    # echoed token proves CSRF validation passes (405 method-not-allowed,
    # not a 403 CSRF rejection).
    response = client.post(
        "/api/auth/csrf/",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 405
