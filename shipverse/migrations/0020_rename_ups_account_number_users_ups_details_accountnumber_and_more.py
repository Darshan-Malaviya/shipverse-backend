# Generated by Django 4.2.7 on 2023-12-01 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0019_rename_counrty_users_ups_details_counrty2_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='users_ups_details',
            old_name='UPS_account_number',
            new_name='accountNumber',
        ),
        migrations.AlterField(
            model_name='users_ups_details',
            name='phone',
            field=models.BigIntegerField(),
        ),
    ]
