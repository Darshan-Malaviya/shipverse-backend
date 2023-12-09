# Generated by Django 4.2.7 on 2023-12-09 03:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0024_alter_users_customerid_alter_users_email_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='users',
            name='customerId',
            field=models.CharField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='email',
            field=models.EmailField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='fullName',
            field=models.CharField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='parentuser',
            field=models.CharField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='password',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='phone',
            field=models.CharField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='roles',
            field=models.CharField(max_length=70, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='usertype',
            field=models.CharField(max_length=70, null=True),
        ),
    ]