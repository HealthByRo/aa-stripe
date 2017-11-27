# -*- coding: utf-8 -*-
import logging

import stripe
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import JSONField, ModelSerializer

from aa_stripe.models import StripeCoupon, StripeCustomer, StripeWebhook

logging.getLogger("aa-stripe")


class StripeCouponSerializer(ModelSerializer):
    class Meta:
        model = StripeCoupon
        fields = [
            "coupon_id", "amount_off", "currency", "duration", "duration_in_months", "livemode", "max_redemptions",
            "metadata", "percent_off", "redeem_by", "times_redeemed", "valid", "is_created_at_stripe", "created",
            "updated", "is_deleted"
        ]


class StripeCustomerSerializer(ModelSerializer):
    stripe_js_response = JSONField()

    def create(self, validated_data):
        instance = None
        if validated_data.get("stripe_js_response"):
            # Create a Customer
            try:
                user = self.context['request'].user
                stripe_js_response = validated_data.pop("stripe_js_response")
                instance = StripeCustomer.objects.create(
                    user=user, stripe_js_response=stripe_js_response)
                instance.create_at_stripe()
            except stripe.StripeError as e:
                logging.error(
                    "[AA-Stripe] creating customer failed for user {user.id}: {{ error }}".format(user=user, error=e)
                )
                raise ValidationError({"stripe_js_response": e})

        return instance

    class Meta:
        model = StripeCustomer
        fields = ["stripe_js_response"]


class StripeWebhookSerializer(ModelSerializer):

    class Meta:
        model = StripeWebhook
        fields = ["id", "raw_data"]
