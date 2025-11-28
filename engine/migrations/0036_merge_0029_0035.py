# Generated merge migration to resolve conflict between 0029 and 0035

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0029_alter_subscriptionplan_options_and_more"),
        ("engine", "0035_add_keywords_journals_to_paper"),
    ]

    operations = [
        # This is a merge migration - no operations needed
        # It just merges the two migration branches
    ]

