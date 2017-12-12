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
                    {"exp_month": 8, "exp_year": 2018, "last4": "4242"}
                ],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/cus_xyz/sources"
            }
        }
        m.register_uri("GET", "https://api.stripe.com/v1/customers/cus_xyz", status_code=200,
                       text=json.dumps(stripe_customer_response))

    def setUp(self):
        self._create_user()
        self._create_customer("cus_xyz")

    def test_save(self):
        # test creating from JS response, Stripe API should not be called
        self.assertIsNone(self.customer.default_card)
        card = self._create_card()
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.default_card, card)

        # test creating another card from JS response
        # default_card for the customer is already set and should not be updated
        card = self._create_card()
        self.customer.refresh_from_db()
        self.assertNotEqual(self.customer.default_card, card)

    @requests_mock.Mocker()
    def test_update(self, m):
        card = self._create_card(stripe_card_id="card_xyz")
        # test updating a card that no longer exists at Stripe
        stripe_card_response = {"id": "card_xyz", "object": "card", "customer": "cus_xyz"}
        self._setup_customer_api_mock(m)
        m.register_uri(
            "GET", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_xyz", [
                {"status_code": 404, "text": json.dumps({"error": {"type": "invalid_request_error"}})},
                {"status_code": 200, "text": json.dumps(stripe_card_response)}
            ])
        m.register_uri(
            "POST", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_xyz", status_code=200,
            text=json.dumps(stripe_card_response)
        )
        card.exp_year = 2020
        card.save()
        deleted_qs = StripeCard.objects.deleted()
        self.assertTrue(deleted_qs.filter(pk=card.pk).exists())

        # test correct update (card exists)
        card = self._create_card(stripe_card_id="card_xyz")
        card.exp_year = 2017
        card.save()
        self.assertFalse(deleted_qs.filter(pk=card.pk).exists())

    @requests_mock.Mocker()
    def test_delete(self, m):
        # try deleting card that does not exist at Stripe API - should not call Stripe (DELETE)
        self._setup_customer_api_mock(m)
        m.register_uri(
            "GET", "https://api.stripe.com/v1/customers/cus_xyz/sources/card_xyz", status_code=404,
            text=json.dumps({"error": {"type": "invalid_request_error"}}))
        self._create_card(stripe_card_id="card_xyz")
        StripeCard.objects.filter(pk=self.card.pk).update(is_deleted=True)
        StripeCard.objects.all_with_deleted().get(pk=self.card.pk).delete()
