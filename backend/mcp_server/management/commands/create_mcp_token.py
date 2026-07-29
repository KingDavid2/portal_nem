"""`manage.py create_mcp_token` — mint an API token for a given membership.

Prints the raw token exactly once; it cannot be retrieved again.
No HTTP surface mints tokens in v1 — issuance is command-only.
"""

from __future__ import annotations

import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError
from workspaces.models import Membership

from mcp_server.models import WorkspaceApiToken


class Command(BaseCommand):
    help = "Mint a new API token for a membership and print the raw value once."

    def add_arguments(self, parser):
        parser.add_argument(
            "--membership",
            required=True,
            type=int,
            help="Membership ID to mint the token for.",
        )
        parser.add_argument(
            "--name",
            required=True,
            help="Human-readable name/label for the token.",
        )

    def handle(self, *args, **options):
        membership_id = options["membership"]
        name = options["name"]

        try:
            membership = Membership.objects.get(pk=membership_id)
        except Membership.DoesNotExist:
            raise CommandError(f"Membership {membership_id} not found.")

        # Generate raw token (256 bits of randomness, hex-encoded = 64 chars)
        raw_token = secrets.token_hex(32)

        # Compute and store only the SHA-256 hash
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Create token row (no scope required — plain Model)
        WorkspaceApiToken.objects.create(
            membership=membership,
            name=name,
            token_hash=token_hash,
        )

        # Print raw token exactly once with explicit notice
        message = (
            f"Token created:\n"
            f"  Name: {name}\n"
            f"  Raw token: {raw_token}\n\n"
        )
        self.stdout.write(message)
        self.stderr.write(
            self.style.WARNING(
                "⚠️  This is the ONLY time you will see this token.\n"
                "It cannot be retrieved again from the database."
            )
        )