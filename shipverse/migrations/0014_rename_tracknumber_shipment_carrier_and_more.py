# Generated by Django 4.2.2 on 2023-09-08 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0013_remove_internationalsettings_customdeclarations_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shipment',
            old_name='tracknumber',
            new_name='carrier',
        ),
        migrations.AddField(
            model_name='shipment',
            name='datecreated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='shipment',
            name='trackingnumber',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='shipment',
            name='trackingurl',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
    ]
