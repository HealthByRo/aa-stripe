# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-08 15:03
from __future__ import unicode_literals

import django.core.validators
import django.db.models.deletion
import jsonfield.fields
from django.conf import settings
from django.db import migrations, models


USER_MODEL = getattr(settings, "STRIPE_USER_MODEL", settings.AUTH_USER_MODEL)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(USER_MODEL),
        ('aa_stripe', '0002_auto_20170607_0714'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeCustomer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('stripe_response', jsonfield.fields.JSONField(default=dict)),
                ('stripe_js_response', jsonfield.fields.JSONField(default=dict)),
                ('stripe_customer_id', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('is_created_at_stripe', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='stripe_customers', to=USER_MODEL)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='StripeSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('stripe_response', jsonfield.fields.JSONField(default=dict)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=255)),
                ('is_created_at_stripe', models.BooleanField(default=False)),
                ('status', models.CharField(blank=True, choices=[('trialing', 'trialing'), ('active', 'active'), ('past_due', 'past_due'), ('canceled', 'canceled'), ('unpaid', 'unpaid')], help_text='https://stripe.com/docs/api/python#subscription_object-status, empty if not sent created at stripe', max_length=255)),
                ('metadata', jsonfield.fields.JSONField(default=dict, help_text='https://stripe.com/docs/api/python#create_subscription-metadata')),
                ('tax_percent', models.DecimalField(decimal_places=2, default=0, help_text='https://stripe.com/docs/api/python#subscription_object-tax_percent', max_digits=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('application_fee_percent', models.DecimalField(decimal_places=2, default=0, help_text='https://stripe.com/docs/api/python#create_subscription-application_fee_percent', max_digits=3, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('coupon', models.CharField(blank=True, help_text='https://stripe.com/docs/api/python#create_subscription-coupon', max_length=255)),
                ('customer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='aa_stripe.StripeCustomer')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StripeSubscriptionPlan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('stripe_response', jsonfield.fields.JSONField(default=dict)),
                ('is_created_at_stripe', models.BooleanField(default=False)),
                ('source', jsonfield.fields.JSONField(blank=True, default=dict, help_text='Source of the plan, ie: {"prescription": 1}')),
                ('amount', models.IntegerField(help_text='In cents. More: https://stripe.com/docs/api#create_plan-amount')),
                ('currency', models.CharField(default='USD', help_text='3 letter ISO code, default USD, , https://stripe.com/docs/api#create_plan-currency', max_length=3)),
                ('name', models.CharField(help_text='Name of the plan, to be displayed on invoices and in the web interface.', max_length=255)),
                ('interval', models.CharField(choices=[('day', 'day'), ('week', 'week'), ('month', 'month'), ('year', 'year')], help_text='Specifies billing frequency. Either day, week, month or year.', max_length=10)),
                ('interval_count', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('metadata', jsonfield.fields.JSONField(default=dict, help_text='A set of key/value pairs that you can attach to a plan object. It can be useful for storing additional information about the plan in a structured format.')),
                ('statement_descriptor', models.CharField(blank=True, help_text='An arbitrary string to be displayed on your customer’s credit card statement.', max_length=22)),
                ('trial_period_days', models.IntegerField(default=0, help_text='Specifies a trial period in (an integer number of) days. If you include a trial period, the customer won’t be billed for the first time until the trial period ends. If the customer cancels before the trial period is over, she’ll never be billed at all.', validators=[django.core.validators.MinValueValidator(0)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StripeWebhook',
            fields=[
                ('id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('created', models.DateField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_parsed', models.BooleanField(default=False)),
                ('raw_data', jsonfield.fields.JSONField(default=dict)),
            ],
        ),
        migrations.RemoveField(
            model_name='stripetoken',
            name='user',
        ),
        migrations.RemoveField(
            model_name='stripecharge',
            name='token',
        ),
        migrations.AddField(
            model_name='stripecharge',
            name='stripe_response',
            field=jsonfield.fields.JSONField(default=dict),
        ),
        migrations.DeleteModel(
            name='StripeToken',
        ),
        migrations.AddField(
            model_name='stripesubscription',
            name='plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='aa_stripe.StripeSubscriptionPlan'),
        ),
        migrations.AddField(
            model_name='stripesubscription',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stripe_subscriptions',
                                    to=USER_MODEL),
        ),
        migrations.AddField(
            model_name='stripecharge',
            name='customer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='aa_stripe.StripeCustomer'),
        ),
    ]
