# Generated by Django 4.2.7 on 2023-12-13 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0027_rename_contact_number_candapostuserdetails_contract_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usercarrier',
            name='phone',
            field=models.CharField(),
        ),
        migrations.AlterField(
            model_name='usercarrier',
            name='postcode',
            field=models.CharField(),
        ),
        migrations.AlterField(
            model_name='usercarrier',
            name='zip_code',
            field=models.CharField(),
        ),
    ]
