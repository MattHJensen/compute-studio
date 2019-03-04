# Generated by Django 2.1.5 on 2019-03-04 22:10

import django.contrib.postgres.fields
from django.db import migrations, models
import webapp.apps.users.models


class Migration(migrations.Migration):

    dependencies = [("users", "0007_project_status")]

    operations = [
        migrations.RemoveField(model_name="project", name="server_cpu"),
        migrations.RemoveField(model_name="project", name="server_ram"),
        migrations.AddField(
            model_name="project",
            name="server_size",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=5),
                default=webapp.apps.users.models.Project.callabledefault,
                size=2,
            ),
        ),
    ]
