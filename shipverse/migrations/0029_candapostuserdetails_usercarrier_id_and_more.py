# Generated by Django 4.2.7 on 2023-12-14 09:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0028_alter_usercarrier_phone_alter_usercarrier_postcode_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='candapostuserdetails',
            name='usercarrier_id',
            field=models.CharField(max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='usercarrier',
            name='token_id',
            field=models.CharField(max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name='usercarrier',
            name='postcode',
            field=models.CharField(max_length=100),
        ),
    ]