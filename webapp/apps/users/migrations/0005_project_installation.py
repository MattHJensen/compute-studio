# Generated by Django 2.1.5 on 2019-02-22 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0004_auto_20190222_1322")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="installation",
            field=models.CharField(default="", max_length=1000),
            preserve_default=False,
        )
    ]