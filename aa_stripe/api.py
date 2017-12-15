import simplejson as json
import stripe
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from aa_stripe.models import StripeCard, StripeCoupon, StripeCustomer, StripeWebhook
from aa_stripe.serializers import (StripeCardCreateSerializer, StripeCardListSerializer, StripeCouponSerializer,
                                   StripeCustomerRetriveSerializer, StripeCustomerSerializer, StripeWebhookSerializer)
from aa_stripe.settings import stripe_settings


class StripeCardsAPI(ListCreateAPIView):
    queryset = StripeCard.objects.all()
    serializer_class = StripeCardListSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if hasattr(self, "request") and self.request.method == "POST":
            return StripeCardCreateSerializer
        return self.serializer_class


class CouponDetailsAPI(RetrieveAPIView):
    queryset = StripeCoupon.objects.all()
    serializer_class = StripeCouponSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "coupon_id"


class CustomersAPI(CreateAPIView, RetrieveModelMixin):
    queryset = StripeCustomer.objects.all()
    serializer_class = StripeCustomerSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), user=self.request.user)

    def get_serializer_class(self):
        if hasattr(self, "request") and self.request.method == "GET":
            return StripeCustomerRetriveSerializer
        return self.serializer_class

    def get(self, request):
        return self.retrieve(request)


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
