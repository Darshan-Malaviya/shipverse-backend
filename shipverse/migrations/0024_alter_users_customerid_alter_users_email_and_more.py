# Generated by Django 4.2.7 on 2023-12-08 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0023_rename_counrty_usercarrier_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='users',
            name='customerId',
            field=models.CharField(default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='email',
            field=models.EmailField(blank=True, default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='fullName',
            field=models.CharField(blank=True, default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='parentuser',
            field=models.CharField(default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='password',
            field=models.CharField(default=None, max_length=500),
        ),
        migrations.AlterField(
            model_name='users',
            name='phone',
            field=models.CharField(blank=True, default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='roles',
            field=models.CharField(default=None, max_length=70),
        ),
        migrations.AlterField(
            model_name='users',
            name='usertype',
            field=models.CharField(blank=True, default=None, max_length=70),
        ),
    ]
