# -*- coding: utf-8 -*-
from django.contrib import admin

from django_stripe.models import StripeCharge, StripeToken


class StripeTokenAdmin(admin.ModelAdmin):
    readonly_fields = ("created", "updated", "user", "content", "customer_id", "is_active")
    list_display = ("id", "user", "created", "is_active")


class StripeChargeAdmin(admin.ModelAdmin):
    readonly_fields = ("created", "updated", "user", "token", "amount", "is_charged", "stripe_charge_id",
                       "description", "comment")
    list_display = ("id", "user", "token", "created", "updated", "is_charged", "amount")


admin.site.register(StripeToken, StripeTokenAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
