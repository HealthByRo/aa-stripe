import simplejson as json
import stripe
from aa_stripe.models import StripeCustomer, StripeWebhook
from aa_stripe.serializers import StripeCustomerSerializer, StripeWebhookSerializer
from django.conf import settings
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


class CustomersAPI(CreateAPIView):
    queryset = StripeCustomer.objects.all()
    serializer_class = StripeCustomerSerializer
    permission_classes = (IsAuthenticated,)


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
                payload, sig_header, settings.STRIPE_WEBHOOK_ENDPOINT_SECRET, api_key=settings.STRIPE_API_KEY,
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
