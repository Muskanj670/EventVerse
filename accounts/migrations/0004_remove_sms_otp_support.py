from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_verificationotp_cleanup_profile_flags'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='phone_verified',
        ),
    ]
