from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rag", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="searchmodel",
            name="retrieved_chunks",
            field=models.JSONField(default=list),
        ),
    ]
