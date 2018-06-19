import simplejson as json
import stripe
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from aa_stripe.models import StripeCoupon, StripeCustomer, StripeWebhook
from aa_stripe.serializers import (StripeCouponSerializer, StripeCustomerDetailsSerializer, StripeCustomerSerializer,
                                   StripeWebhookSerializer)
from aa_stripe.settings import stripe_settings


class CouponDetailsAPI(RetrieveAPIView):
    queryset = StripeCoupon.objects.all()
    serializer_class = StripeCouponSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "coupon_id"


class CustomersAPI(CreateAPIView):
    queryset = StripeCustomer.objects.all()
    serializer_class = StripeCustomerSerializer
    permission_classes = (IsAuthenticated,)


class CustomerDetailsAPI(RetrieveUpdateAPIView):
    queryset = StripeCustomer.objects.all()
    serializer_class = StripeCustomerDetailsSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "stripe_customer_id"

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class WebhookAPI(CreateAPIView):
    queryset = StripeWebhook.objects.all()
    serializer_class = StripeWebhookSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        payload = request.body.decode("utf-8")
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, stripe_settings.WEBHOOK_ENDPOINT_SECRET, api_key=stripe_settings.API_KEY,
            )
        except ValueError:
            # Invalid payload
            return Response(status=400, data={"message": "invalid payload"})
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            return Response(status=400, data={"message": str(e)})
        data = {
            "raw_data": json.loads(str(event)),
            "id": event["id"],
        }
        try:
            StripeWebhook.objects.get(pk=event["id"])
            return Response(status=400, data={"message": "already received"})
        except StripeWebhook.DoesNotExist:
            # correct, first time. Create webhook
            webhook = StripeWebhook.objects.create(id=event["id"], raw_data=data["raw_data"])

        serializer = self.serializer_class(webhook)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
