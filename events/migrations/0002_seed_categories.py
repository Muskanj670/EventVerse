from django.db import migrations


def seed_categories(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    for name in ['Technology', 'Business', 'Art & Creativity', 'Workshop']:
        Category.objects.get_or_create(name=name)


def reverse_seed_categories(apps, schema_editor):
    Category = apps.get_model('events', 'Category')
    Category.objects.filter(name__in=['Technology', 'Business', 'Art & Creativity', 'Workshop']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_seed_categories),
    ]
