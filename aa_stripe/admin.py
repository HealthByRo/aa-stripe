# -*- coding: utf-8 -*-
from aa_stripe.models import StripeCharge, StripeToken
from django.contrib import admin


class StripeTokenAdmin(admin.ModelAdmin):
    readonly_fields = ("created", "updated", "user", "stripe_js_response", "customer_id")
    list_display = ("id", "user", "created", "is_active")

    def has_delete_permission(self, request, obj=None):
        return False


class StripeChargeAdmin(admin.ModelAdmin):
    readonly_fields = ("created", "updated", "user", "token", "amount", "is_charged", "stripe_charge_id",
                       "description", "comment")
    list_display = ("id", "user", "token", "created", "updated", "is_charged", "amount")

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(StripeToken, StripeTokenAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
