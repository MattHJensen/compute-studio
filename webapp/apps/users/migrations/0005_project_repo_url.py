# Generated by Django 2.2.1 on 2019-05-03 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0004_auto_20190501_1406")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="repo_url",
            field=models.URLField(default="https://github.com"),
            preserve_default=False,
        )
    ]