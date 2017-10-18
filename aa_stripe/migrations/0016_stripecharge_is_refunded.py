# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aa_stripe', '0015_auto_20170925_0838'),
    ]

    operations = [
        migrations.AddField(
            model_name='stripecharge',
            name='is_refunded',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='stripecharge',
            name='stripe_refund_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
