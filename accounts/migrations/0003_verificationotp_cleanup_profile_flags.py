from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userprofile_verification_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='email_verification_token',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='phone_verification_code',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='phone_verification_sent_at',
        ),
        migrations.CreateModel(
            name='VerificationOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target', models.CharField(max_length=255)),
                ('channel', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS')], max_length=20)),
                ('purpose', models.CharField(choices=[('signup_email', 'Signup Email'), ('signup_phone', 'Signup Phone')], max_length=30)),
                ('code', models.CharField(max_length=6)),
                ('is_verified', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
