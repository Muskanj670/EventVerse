import uuid

from django.db import migrations, models


def populate_email_tokens(apps, schema_editor):
    UserProfile = apps.get_model('accounts', 'UserProfile')
    for profile in UserProfile.objects.filter(email_verification_token__isnull=True):
        profile.email_verification_token = uuid.uuid4()
        profile.save(update_fields=['email_verification_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email_verification_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_verification_code',
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_verification_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(populate_email_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userprofile',
            name='email_verification_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
