# Generated by Django 4.2.7 on 2023-12-01 20:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0020_rename_ups_account_number_users_ups_details_accountnumber_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='users_ups_details',
            old_name='fullname',
            new_name='fullName',
        ),
    ]
