# Generated by Django 5.1.6 on 2025-02-11 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("qrcodes", "0004_qrcode_event_image_qrcode_event_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="date",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="event",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="event",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="qrmask/"),
        ),
    ]
