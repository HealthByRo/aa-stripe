# -*- coding: utf-8 -*-
from django.contrib import admin

from aa_stripe.forms import StripeCouponForm
from aa_stripe.models import (StripeCharge, StripeCoupon, StripeCustomer, StripeSubscription, StripeSubscriptionPlan,
                              StripeWebhook)


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
    ordering = ("-created",)


class StripeChargeAdmin(ReadOnly):
    search_fields = ("user__email", "customer__stripe_customer_id")
    list_display = ("id", "user", "stripe_customer_id", "created", "updated", "object_id", "is_charged", "amount")
    list_filter = ("created", "updated", "is_charged")
    ordering = ("-created",)

    def stripe_customer_id(self, obj):
        if obj.customer:
            return obj.customer.stripe_customer_id


class StripeCouponAdmin(admin.ModelAdmin):
    form = StripeCouponForm
    list_display = ("id", "coupon_id", "amount_off", "percent_off", "currency", "created", "is_deleted",
                    "is_created_at_stripe")
    list_filter = ("coupon_id", "amount_off", "percent_off", "currency", "created", "is_deleted",
                   "is_created_at_stripe")
    readonly_fields = ("stripe_response", "created", "updated", "is_deleted")
    ordering = ("-created",)

    def get_queryset(self, request):
        return StripeCoupon.objects.all_with_deleted()

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field for field in self.form.Meta.fields if field not in ["metadata"]]

        return self.readonly_fields


class StripeSubscriptionAdmin(ReadOnly):
    list_display = (
        "id", "stripe_subscription_id", "user", "is_created_at_stripe", "status", "created", "updated", "end_date",
        "canceled_at")
    ordering = ("-created",)


class StripeSubscriptionPlanAdmin(ReadOnly):
    list_display = ("id", "is_created_at_stripe", "created", "updated", "amount", "interval", "interval_count")
    ordering = ("-created",)


class StripeWebhookAdmin(ReadOnly):
    list_display = ("id", "created", "updated", "is_parsed")
    ordering = ("-created",)


admin.site.register(StripeCustomer, StripeCustomerAdmin)
admin.site.register(StripeCharge, StripeChargeAdmin)
admin.site.register(StripeCoupon, StripeCouponAdmin)
admin.site.register(StripeSubscription, StripeSubscriptionAdmin)
admin.site.register(StripeSubscriptionPlan, StripeSubscriptionPlanAdmin)
admin.site.register(StripeWebhook, StripeWebhookAdmin)
