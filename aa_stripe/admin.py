# -*- coding: utf-8 -*-
from aa_stripe.models import StripeCharge, StripeCustomer, StripeSubscription, StripeSubscriptionPlan
from aa_stripe.utils import ReadOnly
from django.contrib import admin


class StripeCustomerAdmin(ReadOnly):
    list_display = ("id", "user", "created", "is_active")


class StripeChargeAdmin(ReadOnly):
    list_display = ("id", "user", "customer", "created", "updated", "is_charged", "amount")


class StripeSubscriptionAdmin(ReadOnly):
    list_display = ("id", "stripe_subscription_id", "user", "is_created_at_stripe", "status", "created", "updated")


class StripeSubscriptionPlanAdmin(ReadOnly):
    list_display = ("id", "is_created_at_stripe", "created", "updated", "amount", "interval", "interval_count")


admin.site.register(StripeCustomer, StripeCustomerAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
admin.site.register(StripeSubscription, StripeSubscriptionAdmin)
admin.site.register(StripeSubscriptionPlan, StripeSubscriptionPlanAdmin)
