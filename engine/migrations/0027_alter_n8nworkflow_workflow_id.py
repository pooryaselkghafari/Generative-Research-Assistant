from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0026_n8nworkflow_and_template_mapping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='n8nworkflow',
            name='workflow_id',
            field=models.CharField(help_text='n8n workflow ID (string).', max_length=64, unique=True),
        ),
    ]


