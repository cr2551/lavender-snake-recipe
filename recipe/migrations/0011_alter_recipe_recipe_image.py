# Generated by Django 3.2.19 on 2023-07-09 15:10

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0010_userfavourite_userhistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='recipe_image',
            field=models.CharField(default='https://source.unsplash.com/8l8Yl2ruUsg', max_length=200, validators=[django.core.validators.URLValidator()]),
        ),
    ]
