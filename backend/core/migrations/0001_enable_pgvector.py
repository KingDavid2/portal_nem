from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Enable the pgvector extension (required for future embedding columns)."""

    initial = True

    dependencies = []

    operations = [
        CreateExtension("vector"),
    ]
