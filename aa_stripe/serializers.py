# -*- coding: utf-8 -*-
import logging

import stripe
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
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
            except stripe.error.StripeError as e:
                logging.error(
                    "[AA-Stripe] creating customer failed for user {user.id}: {error}".format(user=user, error=e)
                )
                raise ValidationError({"stripe_error": e._message})

        return instance

    class Meta:
        model = StripeCustomer
        fields = ["stripe_js_response"]


class StripeCustomerDetailsSerializer(ModelSerializer):
    # source data from Stripe JS response used to add a new card
    stripe_js_response = serializers.JSONField(write_only=True, required=True)
    sources = serializers.JSONField(read_only=True)

    def validate_stripe_js_response(self, value):
        if "id" not in value:
            raise serializers.ValidationError(_("This field must contain JSON data from Stripe JS."))
        return value

    def validate(self, data):
        if "stripe_js_response" not in data:
            raise ValidationError({"stripe_js_response": ["This field is required."]})
        return super(StripeCustomerDetailsSerializer, self).validate(data)

    def update(self, instance, validated_data):
        stripe_js_response = validated_data["stripe_js_response"]
        new_source_token = stripe_js_response["id"]
        try:
            instance.add_new_source(new_source_token, stripe_js_response)
        except stripe.error.StripeError as e:
            logging.error(
                "[AA-Stripe] adding new source to customer failed for user {user.id}: {error}".format(
                    user=self.context["request"].user, error=e)
            )
            raise ValidationError({"stripe_error": e._message})

        return instance

    class Meta:
        model = StripeCustomer
        fields = [
            "id", "user", "stripe_customer_id", "is_active", "sources", "default_source", "default_source_data",
            "stripe_js_response"
        ]
        read_only_fields = ["id", "user", "stripe_customer_id", "is_active", "sources", "default_source"]


class StripeWebhookSerializer(ModelSerializer):

    class Meta:
        model = StripeWebhook
        fields = ["id", "raw_data"]
