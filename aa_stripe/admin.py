# -*- coding: utf-8 -*-
from aa_stripe.models import StripeCharge, StripeCustomer, StripeSubscription, StripeSubscriptionPlan, StripeWebhook
from django.contrib import admin


class ReadOnlyBase(object):
    extra = 0
    extra_fields = []

    def get_readonly_fields(self, request, obj=None):
        from itertools import chain
        field_names = list(set(chain.from_iterable(
            (field.name, field.attname) if hasattr(field, 'attname') else (field.name,)
            for field in self.model._meta.get_fields()
            # For complete backwards compatibility, you may want to exclude
            # GenericForeignKey from the results.
            # if not (field.many_to_one and field.related_model is None)
            # remove all related fields because it causes admin to break
            if not field.one_to_many and not field.one_to_one and not field.auto_created
        )))
        fields = list(self.extra_fields)
        for field in field_names:
            if not hasattr(self, "editable_fields") or (field not in self.editable_fields):
                fields.append(field)
        return fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, *args, **kwargs):
        return False


class ReadOnly(ReadOnlyBase, admin.ModelAdmin):
    editable_fields = []


class StripeCustomerAdmin(ReadOnly):
    list_display = ("id", "user", "created", "is_active")


class StripeChargeAdmin(ReadOnly):
    list_display = ("id", "user", "customer", "created", "updated", "is_charged", "amount")


class StripeSubscriptionAdmin(ReadOnly):
    list_display = ("id", "stripe_subscription_id", "user", "is_created_at_stripe", "status", "created", "updated")


class StripeSubscriptionPlanAdmin(ReadOnly):
    list_display = ("id", "is_created_at_stripe", "created", "updated", "amount", "interval", "interval_count")


class StripeWebhookAdmin(ReadOnly):
    list_display = ("id", "created", "updated", "is_parsed")


admin.site.register(StripeCustomer, StripeCustomerAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
admin.site.register(StripeSubscription, StripeSubscriptionAdmin)
admin.site.register(StripeSubscriptionPlan, StripeSubscriptionPlanAdmin)
admin.site.register(StripeWebhook, StripeWebhookAdmin)
