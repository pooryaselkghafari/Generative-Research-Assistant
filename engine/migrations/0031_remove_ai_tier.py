# Generated migration to remove ai_tier field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0030_add_updated_at_to_subscriptionplan"),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscriptionplan',
            name='ai_tier',
        ),
    ]

