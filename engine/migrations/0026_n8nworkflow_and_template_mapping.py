from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0025_add_agent_template'),
    ]

    operations = [
        migrations.CreateModel(
            name='N8nWorkflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('workflow_id', models.IntegerField(help_text='n8n internal workflow ID', unique=True)),
                ('name', models.CharField(max_length=255)),
                ('active', models.BooleanField(default=False)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('version_id', models.CharField(blank=True, max_length=100)),
                ('webhook_id', models.CharField(blank=True, max_length=100)),
                ('test_url', models.URLField(blank=True)),
                ('production_url', models.URLField(blank=True)),
                ('description', models.TextField(blank=True)),
                ('data', models.JSONField(blank=True, default=dict, help_text='Raw workflow payload for reference')),
                ('n8n_created_at', models.DateTimeField(blank=True, null=True)),
                ('n8n_updated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'n8n Workflow',
                'verbose_name_plural': 'n8n Workflows',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='agenttemplate',
            name='workflow',
            field=models.ForeignKey(blank=True, help_text='Optional: Link this template to a synced n8n workflow for easier management.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agent_templates', to='engine.n8nworkflow'),
        ),
        migrations.AddField(
            model_name='subscriptiontiersettings',
            name='workflow_template',
            field=models.ForeignKey(blank=True, help_text='Associate this subscription tier with an Agent Template (n8n workflow) for chatbot access.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscription_tiers', to='engine.agenttemplate'),
        ),
    ]


