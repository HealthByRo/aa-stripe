from aa_stripe.models import StripeToken
from aa_stripe.serializers import StripeTokenSerializer
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated


class TokensAPI(CreateAPIView):
    queryset = StripeToken.objects.all()
    serializer_class = StripeTokenSerializer
    permission_classes = (IsAuthenticated,)
