from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_registration_cancelled_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='cancelled_seat_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
