# -*- coding: utf-8 -*-
import stripe
from aa_stripe.models import StripeCustomer, StripeWebhook
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer, JSONField


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
                raise ValidationError({"stripe_js_response": e})

        return instance

    class Meta:
        model = StripeCustomer
        fields = ["stripe_js_response"]


class StripeWebhookSerializer(ModelSerializer):

    class Meta:
        model = StripeWebhook
        fields = ["id", "raw_data"]
