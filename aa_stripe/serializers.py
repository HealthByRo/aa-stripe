# -*- coding: utf-8 -*-
import stripe
from aa_stripe.models import StripeCustomer
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer


class StripeCustomerSerializer(ModelSerializer):
    def create(self, validated_data):
        if validated_data.get("stripe_js_response"):
            # Create a Customer
            try:
                user = self.context['request'].user
                stripe.api_key = settings.STRIPE_API_KEY
                stripe_js_response = validated_data.pop("stripe_js_response")
                customer = stripe.Customer.create(
                    source=stripe_js_response["id"],
                    description="{user.first_name} {user.last_name} id: {user.id}".format(user=user)
                )
                instance = StripeCustomer.objects.create(
                    user=user, stripe_customer_id=customer["id"], stripe_js_response=stripe_js_response)
            except stripe.StripeError as e:
                raise ValidationError({"stripe_js_response": e.message})

        return instance

    class Meta:
        model = StripeCustomer
        fields = ["stripe_js_response"]
