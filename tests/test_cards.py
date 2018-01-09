from datetime import datetime
from functools import partial
from itertools import product
from random import randint
from uuid import uuid4

import requests_mock
import simplejson as json
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.reverse import reverse
from tests.test_utils import BaseTestCase

from aa_stripe.models import StripeCard


class BaseCardsTestCase(BaseTestCase):
    _last4 = partial(randint, 1000, 9999)
    _exp_month = partial(randint, 1, 12)
    _todays_year = datetime.utcnow().year
    _exp_year = partial(randint, _todays_year + 1, _todays_year + 50)

    def _stripe_card_id(self):
        return "card_{}".format(uuid4().hex[:24])

    def _stripe_card_fingerprint(self):
        return uuid4().hex[:16]


class TestCards(BaseCardsTestCase):
    def _get_successful_retrive_stripe_customer_response(self, id, default_source=None):
        return {
            "id": id,
            "object": "customer",
            "account_balance": 0,
            "created": 1513338196,
            "currency": "usd",
            "default_source": default_source,
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

    def _get_successful_create_stripe_card_response(self,
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

    def _get_new_random_card(self, is_default=True):
        return self._create_card(
            stripe_card_id=self._stripe_card_id(),
            is_default=is_default,
            set_self=False,
            last4=str(self._last4()),
            exp_month=self._exp_month(),
            exp_year=self._exp_year())

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
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/customers/cus_xyz",
            status_code=200,
            text=json.dumps(stripe_customer_response))

    def setUp(self):
        self._create_user()
        self._create_customer("cus_xyz")

    @requests_mock.Mocker()
    def test_delete(self, m):
        self._setup_customer_api_mock(m)
        card = self._get_new_random_card()
        second_card = self._get_new_random_card(False)
        url = reverse("stripe-customers-cards-details", args=[card.stripe_card_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

        # try deleting card that does not exist at Stripe API - should not call Stripe (DELETE)
        self.client.force_authenticate(user=self.user)
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/customers/cus_xyz/sources/{}".format(card.stripe_card_id),
            status_code=404,
            text=json.dumps({
                "error": {
                    "type": "invalid_request_error"
                }
            }))
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(StripeCard.objects.deleted().filter(pk=card.pk).exists())

        card = self._get_new_random_card()
        url = reverse("stripe-customers-cards-details", args=[card.stripe_card_id])
        # try deleting card that exists at Stripe API - should call Stripe and DELETE
        m.register_uri(
            "GET",
            "https://api.stripe.com/v1/customers/cus_xyz/sources/{}".format(card.stripe_card_id),
            status_code=200,
            text=json.dumps({
                "id": card.stripe_card_id,
                "object": "card",
                "customer": "cus_xyz"
            }))
        m.register_uri(
            "DELETE",
            "https://api.stripe.com/v1/customers/cus_xyz/sources/{}".format(card.stripe_card_id),
            status_code=200,
            text=json.dumps({
                "deleted": "true",
                "id": card.stripe_card_id
            }))
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(StripeCard.objects.deleted().filter(pk=card.pk).exists())

        self._create_user(3)
        self._create_customer("cus_abcd")
        self.client.force_authenticate(user=self.user)
        url = reverse("stripe-customers-cards-details", args=[second_card.stripe_card_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_create_card(self):
        self.assertEqual(StripeCard.objects.count(), 0)
        url = reverse("stripe-customers-cards")
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 403)  # not logged

        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 400)  # no source tag

        stripe_card_id = self._stripe_card_id()
        customer_id = self.customer.stripe_customer_id
        last4 = str(self._last4())
        exp_month = self._exp_month()
        exp_year = self._exp_year()
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
                    self._get_successful_create_stripe_card_response(
                        id=stripe_card_id, customer_id=customer_id, last4=last4, exp_month=exp_month,
                        exp_year=exp_year))
            }])
            m.register_uri("GET", "https://api.stripe.com/v1/customers/{}".format(customer_id),
                           [{
                               "text": json.dumps(self._get_successful_retrive_stripe_customer_response(customer_id))
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

        cards_dict = dict((c.stripe_card_id, c) for c in [self._get_new_random_card(), self._get_new_random_card()])

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

        cards_dict = dict(
            (c.stripe_card_id, c)
            for c in [self._get_new_random_card(),
                      self._get_new_random_card(),
                      self._get_new_random_card()])

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200)  # logged in and three cards belonging only to this user
        self.assertEqual(len(response.data), 3)
        for r in response.data:
            self.assertIn(r["stripe_card_id"], cards_dict)
            card = cards_dict[r["stripe_card_id"]]
            self.assertEqual(r["last4"], card.last4)
            self.assertEqual(r["exp_month"], card.exp_month)
            self.assertEqual(r["exp_year"], card.exp_year)

    def test_get_card(self):
        url = reverse("stripe-customers-cards-details", args=[self._stripe_card_id()])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)  # no card

        card_1 = self._get_new_random_card()
        url = reverse("stripe-customers-cards-details", args=[card_1.stripe_card_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stripe_card_id"], card_1.stripe_card_id)
        self.assertEqual(response.data["last4"], card_1.last4)
        self.assertEqual(response.data["exp_month"], card_1.exp_month)
        self.assertEqual(response.data["exp_year"], card_1.exp_year)

        self._create_user(3)
        self._create_customer("cus_abcd")
        card_2 = self._get_new_random_card()
        url = reverse("stripe-customers-cards-details", args=[card_2.stripe_card_id])

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["stripe_card_id"], card_2.stripe_card_id)
        self.assertNotEqual(response.data["stripe_card_id"], card_1.stripe_card_id)

        url = reverse("stripe-customers-cards-details", args=[card_1.stripe_card_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_update_card(self):
        not_existing_stripe_card_id = self._stripe_card_id()
        url = reverse("stripe-customers-cards-details", args=[not_existing_stripe_card_id])
        data = {"stripe_token": "tok_amex", "set_default": True}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 404)

        default_card = self._get_new_random_card()
        other_card = self._get_new_random_card(False)
        cases_map = {
            (True, True): 200,
            (True, False): 200,
            (False, True): 200,
            (False, False): 200,
        }
        for case in cases_map:
            is_default = case[0]
            set_default = case[1]
            return_code = cases_map[case]
            default_card.refresh_from_db()
            other_card.refresh_from_db()
            self.customer.default_card = default_card
            self.customer.save()
            card_to_be_updated = default_card if is_default else other_card

            url = reverse("stripe-customers-cards-details", args=[card_to_be_updated.stripe_card_id])
            data = {"stripe_token": "tok_amex", "set_default": set_default}
            customer_id = self.customer.stripe_customer_id
            updated_card_id = self._stripe_card_id()

            with requests_mock.Mocker() as m:
                m.register_uri(
                    "GET", "https://api.stripe.com/v1/customers/{}".format(customer_id),
                    [{
                        "text": json.dumps(self._get_successful_retrive_stripe_customer_response(customer_id))
                    }])
                m.register_uri(
                    "POST", "https://api.stripe.com/v1/customers/{}".format(customer_id),
                    [{
                        "text":
                        json.dumps(self._get_successful_retrive_stripe_customer_response(customer_id, updated_card_id))
                    }])
                m.register_uri("GET", "https://api.stripe.com/v1/customers/{}/sources/{}".format(
                    customer_id, updated_card_id), [{
                        "text":
                        json.dumps(
                            self._get_successful_create_stripe_card_response(
                                id=updated_card_id,
                                customer_id=customer_id,
                                last4=card_to_be_updated.last4,
                                exp_month=card_to_be_updated.exp_month,
                                exp_year=card_to_be_updated.exp_year))
                    }])
                response = self.client.patch(url, data, format="json")
                self.assertEqual(response.status_code, return_code)

        card_to_be_updated.refresh_from_db()
        self._create_user(3)
        self._create_customer("cus_abcd")
        self.client.force_authenticate(user=self.user)
        url = reverse("stripe-customers-cards-details", args=[card_to_be_updated.stripe_card_id])
        data = {"stripe_token": "tok_amex", "set_default": set_default}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 403)


class TestCardsCommands(BaseCardsTestCase):

    def _get_empty_sources_retrive_customer_stripe_response(self, customer_id):
        return json.loads('''{{
          "id": "{0}",
          "object": "customer",
          "account_balance": 0,
          "created": 1515510882,
          "currency": "usd",
          "default_source": null,
          "delinquent": false,
          "description": null,
          "discount": null,
          "email": null,
          "livemode": false,
          "metadata": {{}},
          "shipping": null,
          "sources": {{
            "object": "list",
            "data": [],
            "has_more": false,
            "total_count": 0,
            "url": "/v1/customers/{0}/sources"
          }},
          "subscriptions": {{
            "object": "list",
            "data": [],
            "has_more": false,
            "total_count": 0,
            "url": "/v1/customers/{0}/subscriptions"
          }}
        }}'''.format(customer_id))

    def _get_retrive_card_stripe_response(self, card_id, customer_id=None):
        if customer_id:
            return json.loads('''{{
            "id": "{0}",
            "object": "card",
            "address_city": null,
            "address_country": null,
            "address_line1": null,
            "address_line1_check": null,
            "address_line2": null,
            "address_state": null,
            "address_zip": null,
            "address_zip_check": null,
            "brand": "Visa",
            "country": "US",
            "customer": "{1}",
            "cvc_check": null,
            "dynamic_last4": null,
            "exp_month": {2},
            "exp_year": {3},
            "fingerprint": "{4}",
            "funding": "credit",
            "last4": "{5}",
            "metadata": {{}},
            "name": null,
            "tokenization_method": null
            }}'''.format(card_id, customer_id, self._exp_month(), self._exp_year(), self._stripe_card_fingerprint(),
                         self._last4()))

        return json.loads('''{{
          "error": {{
            "type": "invalid_request_error",
            "message": "No such source: {}",
            "param": "id"
          }}
        }}'''.format(card_id))

    @requests_mock.Mocker()
    def test_sync_all_cards_for_all_customers_command(self, m):
        cards_created = (0, 2)
        cards_not_changed = (1,)
        cards_updated = (0, 3)
        cards_deleted = (0, 1)
        cards_we_deleted = (0, 1)
        cards_cases = [*product(cards_created, cards_not_changed, cards_updated, cards_deleted, cards_we_deleted)]
        cards_count_in_database_before_command_call = sum([c[1] + c[2] + c[3] + c[4] for c in cards_cases])
        cards_not_deleted_count_in_database_before_command_call = sum([c[1] + c[2] + c[3] for c in cards_cases])
        cards_count_in_database_after_command_call = sum([c[0] + c[1] + c[2] + c[3] + c[4] for c in cards_cases])
        cards_not_deleted_count_in_database_after_command_call = sum([c[0] + c[1] + c[2] + c[4] for c in cards_cases])
        test_cases = {}
        test_update_cases = {c: {} for c in cards_cases}
        for i, case in enumerate(cards_cases):
            self._create_user(i)
            self._create_customer()
            customer_id = self.customer.stripe_customer_id
            created_card_ids = [self._stripe_card_id() for r in range(case[0])]
            not_changed_card_ids = [self._stripe_card_id() for r in range(case[1])]
            updated_card_ids = [self._stripe_card_id() for r in range(case[2])]
            deleted_card_ids = [self._stripe_card_id() for r in range(case[3])]
            we_deleted_card_ids = [self._stripe_card_id() for r in range(case[4])]

            cards_at_stripe = created_card_ids + updated_card_ids + not_changed_card_ids + we_deleted_card_ids
            cards_in_database = updated_card_ids + not_changed_card_ids + deleted_card_ids + we_deleted_card_ids
            default_card_id = (updated_card_ids + not_changed_card_ids)[0]
            swap_default_card = case[0] and case[2] or case[2] and case[3]
            new_default_card = (created_card_ids + updated_card_ids)[1] if swap_default_card else default_card_id

            test_cases[case] = (customer_id, created_card_ids, not_changed_card_ids, updated_card_ids, deleted_card_ids,
                                we_deleted_card_ids, default_card_id, new_default_card)

            customer_response = self._get_empty_sources_retrive_customer_stripe_response(customer_id)
            customer_response["sources"]["total_count"] = len(cards_at_stripe)
            for card_id in cards_at_stripe:
                card_response = self._get_retrive_card_stripe_response(card_id, customer_id)
                customer_response["sources"]["data"].append(card_response)

                if card_id in cards_in_database:
                    if card_id in updated_card_ids:
                        old_exp_month = self._exp_month()
                        old_exp_year = self._exp_year()
                        test_update_cases[case][card_id] = (old_exp_month, old_exp_year, card_response["exp_month"],
                                                            card_response["exp_year"])
                        self._create_card(
                            stripe_card_id=card_id,
                            is_default=card_id == default_card_id,
                            last4=card_response["last4"],
                            exp_month=old_exp_month,
                            exp_year=old_exp_year)
                    else:
                        self._create_card(
                            stripe_card_id=card_id,
                            is_default=card_id == default_card_id,
                            last4=card_response["last4"],
                            exp_month=card_response["exp_month"],
                            exp_year=card_response["exp_year"],
                            is_deleted=card_id in we_deleted_card_ids)

            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/customers/{}/sources?object=card".format(customer_id),
                status_code=200,
                text=json.dumps(customer_response["sources"]))
            m.register_uri(
                "GET",
                "https://api.stripe.com/v1/customers/{}".format(customer_id),
                status_code=200,
                text=json.dumps(customer_response))

            for card_id in deleted_card_ids:
                self._create_card(stripe_card_id=card_id)
                m.register_uri(
                    "GET",
                    "https://api.stripe.com/v1/customers/{}/sources/{}".format(customer_id, card_id),
                    status_code=404,
                    text=json.dumps(self._get_retrive_card_stripe_response(card_id)))

        user_ids = get_user_model().objects.values_list("id")
        min_user_id, max_user_id = min(user_ids)[0], max(user_ids)[0]

        self.assertEqual(StripeCard.objects.all_with_deleted().count(), cards_count_in_database_before_command_call)
        self.assertEqual(StripeCard.objects.count(), cards_not_deleted_count_in_database_before_command_call)
        call_command("sync_all_cards_for_all_customers", patient_id_range="{}_{}".format(min_user_id, max_user_id))
        self.assertEqual(StripeCard.objects.all_with_deleted().count(), cards_count_in_database_after_command_call)
        self.assertEqual(StripeCard.objects.count(), cards_not_deleted_count_in_database_after_command_call)
