"""RED tests for the custom email-identified User model (identity-auth spec)."""

import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_user_created_with_email_as_identifier():
    user = User.objects.create_user(email="teacher@example.com", password="s3cret-pass")
    assert user.email == "teacher@example.com"
    assert user.get_username() == "teacher@example.com"
    assert not hasattr(user, "username") or User.USERNAME_FIELD == "email"


def test_duplicate_email_rejected():
    User.objects.create_user(email="teacher@example.com", password="s3cret-pass")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="teacher@example.com", password="another-pass")


def test_superuser_creation_requires_is_staff_and_is_superuser():
    admin = User.objects.create_superuser(email="admin@example.com", password="s3cret-pass")
    assert admin.is_staff is True
    assert admin.is_superuser is True
