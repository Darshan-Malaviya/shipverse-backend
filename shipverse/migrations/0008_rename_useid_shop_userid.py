# Generated by Django 4.2.2 on 2023-08-23 13:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shipverse', '0007_shop_useid'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shop',
            old_name='useId',
            new_name='userId',
        ),
    ]
