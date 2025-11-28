# Generated manually for adding keywords and target_journals to Paper model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("engine", "0034_alter_aiprovider_api_key_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paper",
            name="keywords",
            field=models.JSONField(blank=True, default=list, help_text="List of keywords for this paper"),
        ),
        migrations.AddField(
            model_name="paper",
            name="target_journals",
            field=models.JSONField(blank=True, default=list, help_text="List of target journal names"),
        ),
    ]

