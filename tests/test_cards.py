import requests_mock
import simplejson as json
from tests.test_utils import BaseTestCase

from aa_stripe.models import StripeCard


class TestCards(BaseTestCase):
    def _setup_customer_api_mock(self, m):
        stripe_customer_response = {
            "id": "cus_xyz",
            "object": "customer",
            "created": 1513013595,
            "currency": "usd",
            "default_source": None,
            "metadata": {
            },
            "sources": {
                "object": "list",
                "data": [
                    {"exp_month": 8, "exp_year": 2018, "last4": "4242", "id": "card_xyz"},
                    {"exp_month": 8, "exp_year": 2018, "last4": "1242", "id": "card_abc"}
                ],
                "has_more": False,
                "total_count": 2,
                "url": "/v1/customers/cus_xyz/sources"
            }
        }
        m.register_uri("GET", "https://api.stripe.com/v1/customers/cus_xyz", status_code=200,
                       text=json.dumps(stripe_customer_response))

    def setUp(self):
        self._create_user()
        self._create_customer("cus_xyz")

    @requests_mock.Mocker()
    def test_delete(self, m):
        # try deleting card that does not exist at Stripe API - should not call Stripe (DELETE)
        self._setup_customer_api_mock(m)
        m.register_uri(
            "GET", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_xyz", status_code=404,
            text=json.dumps({"error": {"type": "invalid_request_error"}}))
        self._create_card(stripe_card_id="card_xyz")
        self.card.delete()
        self.assertTrue(StripeCard.objects.deleted().filter(pk=self.card.pk).exists())

        # try deleting card that exists at Stripe API - should call Stripe and DELETE
        m.register_uri(
            "GET", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_abc", status_code=200,
            text=json.dumps({"id": "card_abc", "object": "card", "customer": "cus_xyz"}))
        m.register_uri(
            "DELETE", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_abc", status_code=200,
            text=json.dumps({"deleted": "true", "id": "card_xyz"})
        )
        card = self._create_card(stripe_card_id="card_abc")
        card.delete()
        self.assertTrue(StripeCard.objects.deleted().filter(pk=card.pk).exists())
