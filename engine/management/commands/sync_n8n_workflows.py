from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from engine.models import N8nWorkflow
from engine.services.n8n_api_client import N8nAPIClient


class Command(BaseCommand):
    help = "Sync workflows from n8n into the local database."

    def add_arguments(self, parser):
        parser.add_argument('--base-url', help="Override n8n API base URL")

    def handle(self, *args, **options):
        client = N8nAPIClient(base_url=options.get('base_url'))
        try:
            workflows = client.list_workflows()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to fetch workflows: {exc}"))
            return

        created = 0
        updated = 0

        for wf in workflows:
            defaults = {
                'name': wf.get('name') or f"Workflow {wf.get('id')}",
                'active': wf.get('active', False),
                'tags': wf.get('tags') or [],
                'version_id': str(wf.get('versionId') or ''),
                'webhook_id': str(wf.get('webhookId') or ''),
                'test_url': wf.get('testUrl', '') or '',
                'production_url': wf.get('productionUrl', '') or '',
                'description': (wf.get('settings') or {}).get('notes', ''),
                'data': wf,
                'n8n_created_at': parse_datetime(wf.get('createdAt')) if wf.get('createdAt') else None,
                'n8n_updated_at': parse_datetime(wf.get('updatedAt')) if wf.get('updatedAt') else None,
            }
            _, is_created = N8nWorkflow.objects.update_or_create(
                workflow_id=wf.get('id'),
                defaults=defaults
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Synced {len(workflows)} workflow(s). Created: {created}, Updated: {updated}"
        ))

