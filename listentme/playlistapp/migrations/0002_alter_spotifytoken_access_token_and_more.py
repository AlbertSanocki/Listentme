# Generated by Django 4.0.6 on 2022-09-08 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playlistapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='spotifytoken',
            name='access_token',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='spotifytoken',
            name='refresh_token',
            field=models.CharField(max_length=500),
        ),
    ]
