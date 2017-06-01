# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField


class StripeToken(models.Model):
    created = models.DateField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = JSONField()
    customer_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]


class StripeCharge(models.Model):
    created = models.DateField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.ForeignKey(StripeToken, on_delete=models.SET_NULL, null=True)
    amount = models.IntegerField(null=True, help_text=_("in cents"))
    is_charged = models.BooleanField(default=False)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, help_text=_("Description sent to Stripe"))
    comment = models.CharField(max_length=255, help_text=_("Comment for internal information"))
