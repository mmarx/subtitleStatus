# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.utils.timezone import make_aware
from datetime import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('www', '0075_auto_20151211_0137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event_days',
            name='date',
            field=models.DateField(blank=True, default=make_aware(datetime.min)),
        ),
    ]
