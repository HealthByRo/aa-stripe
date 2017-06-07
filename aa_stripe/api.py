from aa_stripe.models import StripeCustomer
from aa_stripe.serializers import StripeCustomerSerializer
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated


class CustomersAPI(CreateAPIView):
    queryset = StripeCustomer.objects.all()
    serializer_class = StripeCustomerSerializer
    permission_classes = (IsAuthenticated,)
