# Generated by Django 2.1.5 on 2019-02-22 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("users", "0003_project_app_name")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="package_defaults",
            field=models.CharField(default="", max_length=1000),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="parse_user_adjustments",
            field=models.CharField(default="", max_length=1000),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="run_simulation",
            field=models.CharField(default="", max_length=1000),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="server_cpu",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="server_ram",
            field=models.IntegerField(null=True),
        ),
    ]