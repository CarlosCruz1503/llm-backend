from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rag", "0002_searchmodel_retrieved_chunks"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentchunkmodel",
            name="header",
            field=models.TextField(blank=True, null=True),
        ),
    ]
