# Generated by Django 4.2.2 on 2023-11-28 14:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0017_alter_users_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='Users_UPS_details',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_nickname', models.CharField(blank=True, max_length=250, null=True)),
                ('fullname', models.CharField(max_length=250)),
                ('company_name', models.CharField(max_length=250)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.IntegerField()),
                ('street1', models.CharField(max_length=250)),
                ('street2', models.CharField(blank=True, max_length=250, null=True)),
                ('city', models.CharField(max_length=250)),
                ('state', models.CharField(max_length=250)),
                ('country', models.CharField(max_length=250)),
                ('zip_code', models.IntegerField()),
                ('UPS_account_number', models.CharField(max_length=250)),
                ('postcode', models.IntegerField()),
                ('counrty', models.CharField(max_length=20)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shipverse.users')),
            ],
        ),
    ]
