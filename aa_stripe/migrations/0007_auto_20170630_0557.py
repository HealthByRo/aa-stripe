# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-30 09:57
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

USER_MODEL = getattr(settings, "STRIPE_USER_MODEL", settings.AUTH_USER_MODEL)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(USER_MODEL),
        ('aa_stripe', '0006_subscription_end_cancel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stripecharge',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='stripe_charges', to=USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stripecustomer',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stripe_customers',
                                    to=USER_MODEL),
        ),
        migrations.AlterField(
            model_name='stripesubscription',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stripe_subscriptions',
                                    to=USER_MODEL),
        ),
    ]