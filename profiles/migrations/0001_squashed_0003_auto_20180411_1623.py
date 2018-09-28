# Generated by Django 1.10 on 2018-04-12 18:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('server', '0068_auto_20180313_1440'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=255)),
                ('identifier', models.CharField(db_index=True, max_length=255)),
                ('uuid', models.CharField(max_length=255)),
            ],
            options={
                'ordering': ['identifier'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('identifier', models.CharField(db_index=True, max_length=255)),
                ('display_name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('install_date', models.DateTimeField()),
                ('organization', models.CharField(max_length=255)),
                ('uuid', models.CharField(max_length=255)),
                ('verification_state', models.CharField(max_length=255)),
                ('machine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='server.Machine')),
            ],
            options={
                'ordering': ['display_name'],
            },
        ),
        migrations.AddField(
            model_name='payload',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='profiles.Profile'),
        ),
        migrations.RenameField(
            model_name='payload',
            old_name='type',
            new_name='payload_type',
        ),
        migrations.AlterField(
            model_name='payload',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]
