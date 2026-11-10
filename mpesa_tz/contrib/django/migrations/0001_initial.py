from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("c2b", "Customer to business"), ("b2c", "Business to customer")], default="c2b", max_length=3)),
                ("phone", models.CharField(max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference", models.CharField(db_index=True, max_length=20)),
                ("description", models.CharField(blank=True, max_length=256)),
                ("third_party_conversation_id", models.CharField(max_length=64, unique=True)),
                ("conversation_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("transaction_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")], default="pending", max_length=10)),
                ("response_code", models.CharField(blank=True, max_length=16)),
                ("response_description", models.CharField(blank=True, max_length=255)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
