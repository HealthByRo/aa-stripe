# -*- coding: utf-8 -*-
import stripe
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField


class StripeToken(models.Model):
    """Actually it is Customer. TODO: rename"""

    created = models.DateField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stripe_tokens')
    stripe_js_response = JSONField()
    customer_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]


class StripeCharge(models.Model):
    created = models.DateField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stripe_charges')
    token = models.ForeignKey(StripeToken, on_delete=models.SET_NULL, null=True)
    amount = models.IntegerField(null=True, help_text=_("in cents"))
    is_charged = models.BooleanField(default=False)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, help_text=_("Description sent to Stripe"))
    comment = models.CharField(max_length=255, help_text=_("Comment for internal information"))

    def charge(self):
        stripe.api_key = settings.STRIPE_API_KEY
        if not self.is_charged and self.token.is_active:
            try:
                stripe_charge = stripe.Charge.create(
                    amount=self.amount,
                    currency="usd",
                    customer=self.token.customer_id,
                    description=self.description
                )
            except stripe.error.StripeError:
                self.is_charged = False
                self.save()
                raise

            self.stripe_charge_id = stripe_charge["id"]
            self.is_charged = True
            self.save()
            return stripe_charge
