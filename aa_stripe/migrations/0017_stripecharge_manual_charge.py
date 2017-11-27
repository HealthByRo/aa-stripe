# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aa_stripe', '0016_stripecharge_is_refunded'),
    ]

    operations = [
        migrations.AddField(
            model_name='stripecharge',
            name='is_manual_charge',
            field=models.BooleanField(default=False),
        ),
    ]
