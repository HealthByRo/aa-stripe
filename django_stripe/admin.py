# -*- coding: utf-8 -*-
from django.contrib import admin

from django_stripe.models import StripeCharge, StripeToken
from django_stripe.utils.admin import ReadOnly


class StripeTokenAdmin(ReadOnly):
    list_display = ("id", "user", "created", "is_active")


class StripeChargeAdmin(ReadOnly):
    list_display = ("id", "user", "token", "created", "updated", "is_charged", "amount")


admin.site.register(StripeToken, StripeTokenAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
