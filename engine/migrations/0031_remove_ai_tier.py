# Generated migration to remove ai_tier field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0028_merge_subscription_models"),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscriptionplan',
            name='ai_tier',
        ),
    ]

