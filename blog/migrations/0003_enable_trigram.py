from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_alter_tag_name'),
    ]

    operations = [
        TrigramExtension()
    ]