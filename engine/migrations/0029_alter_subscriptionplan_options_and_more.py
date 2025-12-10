# Dummy migration to resolve missing 0029 reference
# This migration was created on the server but the file was lost
# It's a placeholder to satisfy migration 0036's dependency

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0028_merge_subscription_models"),
    ]

    operations = [
        # This is a placeholder migration - no operations
        # The actual changes were likely already applied to the database
    ]
