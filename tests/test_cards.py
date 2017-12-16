from datetime import datetime
from functools import partial
from random import randint
from uuid import uuid4

import requests_mock
import simplejson as json
from rest_framework.reverse import reverse
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
            "metadata": {},
            "sources": {
                "object":
                "list",
                "data": [{
                    "exp_month": 8,
                    "exp_year": 2018,
                    "last4": "4242",
                    "id": "card_xyz"
                }, {
                    "exp_month": 8,
                    "exp_year": 2018,
                    "last4": "1242",
                    "id": "card_abc"
                }],
                "has_more":
                False,
                "total_count":
                2,
                "url":
                "/v1/customers/cus_xyz/sources"
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


class TestListCreateCards(BaseTestCase):
    last4 = partial(randint, 1000, 9999)
    exp_month = partial(randint, 1, 12)
    todays_year = datetime.utcnow().year
    exp_year = partial(randint, todays_year, todays_year + 50)

    def stripe_card_id(self):
        return "card_{}".format(uuid4().hex[:24])

    def get_successful_retrive_stripe_customer_response(self, id):
        return {
            "id": id,
            "object": "customer",
            "account_balance": 0,
            "created": 1513338196,
            "currency": "usd",
            "default_source": None,
            "delinquent": False,
            "description": None,
            "discount": None,
            "email": None,
            "livemode": False,
            "metadata": {},
            "shipping": None,
            "sources": {
                "object": "list",
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/{}/sources".format(id)
            },
            "subscriptions": {
                "object": "list",
                "data": [],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/customers/{}/subscriptions".format(id)
            }
        }

    def get_successful_create_stripe_card_response(self,
                                                   id="card_1BZ3932eZvKYlo2CsPjdeVLE",
                                                   customer_id="cus_9Oop0gQ1R1ATMi",
                                                   last4="8431",
                                                   exp_month=8,
                                                   exp_year=2019):
        return {
            "id": id,
            "object": "card",
            "address_city": None,
            "address_country": None,
            "address_line1": None,
            "address_line1_check": None,
            "address_line2": None,
            "address_state": None,
            "address_zip": None,
            "address_zip_check": None,
            "brand": "American Express",
            "country": "US",
            "customer": customer_id,
            "cvc_check": None,
            "dynamic_last4": None,
            "exp_month": exp_month,
            "exp_year": exp_year,
            "fingerprint": "EdFCik9NII3EjtXE",
            "funding": "credit",
            "last4": last4,
            "metadata": {},
            "name": None,
            "tokenization_method": None
        }

    def get_new_random_card(self):
        return self._create_card(
            stripe_card_id=self.stripe_card_id(),
            set_self=False,
            last4=str(self.last4()),
            exp_month=self.exp_month(),
            exp_year=self.exp_year())

    def setUp(self):
        self._create_user()
        self._create_customer("cus_xyz")

    def test_create_card(self):
        self.assertEqual(StripeCard.objects.count(), 0)
        url = reverse("stripe-customers-cards")
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)  # no source tag

        stripe_card_id = self.stripe_card_id()
        customer_id = self.customer.stripe_customer_id
        last4 = str(self.last4())
        exp_month = self.exp_month()
        exp_year = self.exp_year()
        with requests_mock.Mocker() as m:
            m.register_uri("POST", "https://api.stripe.com/v1/customers/{}/sources".format(customer_id), [{
                "text":
                json.dumps({
                    "error": {
                        "type": "invalid_request_error",
                        "message": "No such token: tosdfsdf",
                        "param": "source"
                    }
                }),
                "status_code":
                400
            }, {
                "text":
                json.dumps(
                    self.get_successful_create_stripe_card_response(
                        id=stripe_card_id, customer_id=customer_id, last4=last4, exp_month=exp_month,
                        exp_year=exp_year))
            }])
            m.register_uri("GET", "https://api.stripe.com/v1/customers/{}".format(customer_id),
                           [{
                               "text": json.dumps(self.get_successful_retrive_stripe_customer_response(customer_id))
                           }])

            # test response error
            stripe_card_qs = StripeCard.objects.filter(customer=self.customer, is_created_at_stripe=True)
            data = {"stripe_js_response": {"source": "tosdfsdf"}}
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(m.call_count, 2)
            self.assertEqual(set(response.data.keys()), {"stripe_error"})
            self.assertEqual(response.data["stripe_error"], "No such token: tosdfsdf")
            self.assertEqual(stripe_card_qs.count(), 0)

            # test success response from Stripe
            data = {"stripe_js_response": {"source": "tok_amex"}}
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(m.call_count, 4)
            self.assertEqual(stripe_card_qs.count(), 1)
            card = stripe_card_qs.first()
            self.assertEqual(card.customer, self.customer)
            self.assertEqual(card.stripe_card_id, stripe_card_id)
            self.assertEqual(card.last4, last4)
            self.assertEqual(card.exp_month, exp_month)
            self.assertEqual(card.exp_year, exp_year)

    def test_list_cards(self):
        url = reverse("stripe-customers-cards")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.data, [])  # logged in but no cards
        self.assertEqual(response.status_code, 200)

        cards_dict = dict((c.stripe_card_id, c) for c in [self.get_new_random_card(), self.get_new_random_card()])

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)  # logged in and two cards
        self.assertEqual(len(response.data), 2)
        for r in response.data:
            self.assertIn(r["stripe_card_id"], cards_dict)
            card = cards_dict[r["stripe_card_id"]]
            self.assertEqual(r["last4"], card.last4)
            self.assertEqual(r["exp_month"], card.exp_month)
            self.assertEqual(r["exp_year"], card.exp_year)

        self._create_user(2)
        self._create_customer("cus_abc")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url, format="json")
        self.assertEqual(response.data, [])  # logged in but no cards
        self.assertEqual(response.status_code, 200)

        cards_dict = dict((c.stripe_card_id, c)
                          for c in [self.get_new_random_card(),
                                    self.get_new_random_card(),
                                    self.get_new_random_card()])

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)  # logged in and three cards belonging only to this user
        self.assertEqual(len(response.data), 3)
        for r in response.data:
            self.assertIn(r["stripe_card_id"], cards_dict)
            card = cards_dict[r["stripe_card_id"]]
            self.assertEqual(r["last4"], card.last4)
            self.assertEqual(r["exp_month"], card.exp_month)
            self.assertEqual(r["exp_year"], card.exp_year)
