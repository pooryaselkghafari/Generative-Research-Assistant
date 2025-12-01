# Generated migration for PaperDocument model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0036_merge_0029_0035'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaperDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(help_text='Uploaded document file', upload_to='papers/%Y/%m/%d/')),
                ('original_filename', models.CharField(help_text='Original filename when uploaded', max_length=255)),
                ('file_size', models.BigIntegerField(help_text='File size in bytes')),
                ('file_type', models.CharField(blank=True, help_text='File MIME type or extension', max_length=100)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(blank=True, help_text='Optional description of the document')),
                ('paper', models.ForeignKey(help_text='Paper this document belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='engine.paper')),
            ],
            options={
                'verbose_name': 'Paper Document',
                'verbose_name_plural': 'Paper Documents',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]

