"""Test charging users through the StripeCharge model"""
import sys

import mock
import stripe
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from stripe.error import CardError, StripeError

from aa_stripe.models import StripeCharge, StripeCustomer, StripeMethodNotAllowed
from aa_stripe.signals import stripe_charge_card_exception, stripe_charge_succeeded

UserModel = get_user_model()


class TestCharges(TestCase):
    def _success_handler(self, sender, instance, **kwargs):
        self.success_signal_was_called = True

    def _exception_handler(self, sender, instance, **kwargs):
        self.exception_signal_was_called = True

    def setUp(self):
        self.user = UserModel.objects.create(
            email="foo@bar.bar", username="foo", password="dump-password"
        )
        self.success_signal_was_called = False
        self.exception_signal_was_called = False
        stripe_charge_succeeded.connect(self._success_handler)
        stripe_charge_card_exception.connect(self._exception_handler)
        self.data = {
            "customer_id": "cus_AlSWz1ZQw7qG2z",
            "currency": "usd",
            "amount": 100,
            "description": "ABC",
        }
        self.customer = StripeCustomer.objects.create(
            user=self.user,
            stripe_customer_id=self.data["customer_id"],
            stripe_js_response='"foo"',
        )
        self.charge = StripeCharge.objects.create(
            user=self.user,
            amount=self.data["amount"],
            customer=self.customer,
            description=self.data["description"],
        )

    @mock.patch("aa_stripe.management.commands.charge_stripe.stripe.Charge.create")
    def test_charges(self, charge_create_mocked):
        charge_create_mocked.return_value = stripe.Charge(id="AA1")

        # test in case of an API error
        stripe_error_json_body = {"error": {"type": "api_error"}}
        charge_create_mocked.side_effect = StripeError(json_body=stripe_error_json_body)
        with self.assertRaises(SystemExit):
            out = StringIO()
            sys.stdout = out
            self.success_signal_was_called = False
            self.exception_signal_was_called = False
            call_command("charge_stripe")
            self.assertFalse(self.success_signal_was_called)
            self.assertFalse(self.exception_signal_was_called)
            self.charge.refresh_from_db()
            self.assertFalse(self.charge.is_charged)
            self.assertFalse(self.charge.charge_attempt_failed)
            self.assertDictEqual(self.charge.stripe_response, stripe_error_json_body)
            self.assertIn("Exception happened", out.getvalue())

        # test in case of an hard API error
        charge_create_mocked.reset_mock()
        stripe_error_json_body = {
            "error": {
                "code": "resource_missing",
                "doc_url": "https://stripe.com/docs/error-codes/resource-missing",
                "message": "No such customer: cus_ESrgXHlDA3E7mQ",
                "param": "customer",
                "type": "invalid_request_error",
            }
        }
        charge_create_mocked.side_effect = StripeError(json_body=stripe_error_json_body)
        self.success_signal_was_called = False
        self.exception_signal_was_called = False
        call_command("charge_stripe")
        self.assertFalse(self.success_signal_was_called)
        self.assertTrue(self.exception_signal_was_called)
        self.charge.refresh_from_db()
        self.assertFalse(self.charge.is_charged)
        self.assertTrue(self.charge.charge_attempt_failed)
        self.assertDictEqual(self.charge.stripe_response, stripe_error_json_body)

        # test regular case
        charge_create_mocked.reset_mock()
        card_error_json_body = {
            "error": {
                "charge": "ch_1F5C8nBszOVoiLmgPWC36cnI",
                "code": "card_declined",
                "decline_code": "generic_decline",
                "doc_url": "https://stripe.com/docs/error-codes/card-declined",
                "message": "Your card was declined.",
                "type": "card_error",
            }
        }
        charge_create_mocked.side_effect = CardError(
            message="a", param="b", code="c", json_body=card_error_json_body
        )
        self.success_signal_was_called = False
        self.exception_signal_was_called = False
        self.charge.charge_attempt_failed = False
        self.charge.save()
        call_command("charge_stripe")
        self.assertFalse(self.success_signal_was_called)
        self.assertTrue(self.exception_signal_was_called)
        self.charge.refresh_from_db()
        self.assertFalse(self.charge.is_charged)
        self.assertTrue(self.charge.charge_attempt_failed)
        self.assertDictEqual(self.charge.stripe_response, card_error_json_body)
        self.assertEqual(self.charge.stripe_charge_id, "ch_1F5C8nBszOVoiLmgPWC36cnI")

        # test regular charge case
        charge_create_mocked.reset_mock()
        charge_create_mocked.side_effect = None
        # reset charge
        self.charge.charge_attempt_failed = False
        self.charge.save()
        self.success_signal_was_called = False
        self.exception_signal_was_called = False
        call_command("charge_stripe")
        self.assertTrue(self.success_signal_was_called)
        self.assertFalse(self.exception_signal_was_called)
        self.charge.refresh_from_db()
        self.assertTrue(self.charge.is_charged)
        self.assertEqual(self.charge.stripe_response["id"], "AA1")
        charge_create_mocked.assert_called_with(
            idempotency_key="None-None-None",
            amount=self.charge.amount,
            currency=self.data["currency"],
            customer=self.data["customer_id"],
            description=self.data["description"],
            metadata={"object_id": None, "content_type_id": None},
        )

        # double charge case
        charge_create_mocked.reset_mock()
        self.success_signal_was_called = False
        self.exception_signal_was_called = False
        self.charge.source = self.customer
        self.charge.is_charged = False
        self.charge.save()
        self.charge.charge("idempotency_key")
        self.assertTrue(self.charge.is_charged)
        self.assertTrue(self.success_signal_was_called)
        self.assertFalse(self.exception_signal_was_called)
        self.assertEqual(self.charge.stripe_response["id"], "AA1")
        charge_create_mocked.assert_called_with(
            idempotency_key="{}-{}-{}".format(self.charge.object_id, self.charge.content_type_id, "idempotency_key"),
            amount=self.charge.amount,
            currency=self.data["currency"],
            customer=self.data["customer_id"],
            description=self.data["description"],
            metadata={"object_id": self.charge.object_id, "content_type_id": self.charge.content_type_id},
        )
        # charge on already charged
        with self.assertRaises(StripeMethodNotAllowed) as ctx:
            self.charge.charge()
            self.assertEqual(ctx.exception.args[0], "Already charged.")

    @mock.patch("aa_stripe.management.commands.charge_stripe.stripe.Refund.create")
    def test_refund(self, refund_create_mocked):
        data = {
            "customer_id": "cus_AlSWz1ZQw7qG2z",
            "currency": "usd",
            "amount": 100,
            "description": "ABC",
        }
        refund_create_mocked.return_value = stripe.Refund(id="R1")

        customer = StripeCustomer.objects.create(
            user=self.user,
            stripe_customer_id=data["customer_id"],
            stripe_js_response='"foo"',
        )
        self.assertTrue(
            customer, StripeCustomer.get_latest_active_customer_for_user(self.user)
        )
        charge = StripeCharge.objects.create(
            user=self.user,
            amount=data["amount"],
            customer=customer,
            description=data["description"],
        )
        charge.source = customer

        self.assertFalse(charge.is_refunded)

        # refund - error: not charged
        with self.assertRaises(StripeMethodNotAllowed):
            charge.refund()
            self.assertFalse(charge.is_refunded)

        charge.is_charged = True
        charge.stripe_charge_id = "abc"
        charge.save()
        idempotency_key_prefix = "{}-{}-{}".format(customer.id, charge.content_type_id, 0)

        # partial refund
        with mock.patch("aa_stripe.signals.stripe_charge_refunded.send") as refund_signal_send:
            to_refund = charge.amount - 1
            charge.refund(to_refund)
            refund_create_mocked.assert_called_with(
                charge=charge.stripe_charge_id, amount=to_refund,
                idempotency_key="{}-{}".format(idempotency_key_prefix, to_refund)
            )
            self.assertFalse(charge.is_refunded)
            refund_signal_send.assert_called_with(sender=StripeCharge, instance=charge)
        # refund > amount
        with self.assertRaises(StripeMethodNotAllowed):
            charge.refund(charge.amount + 1)
            self.assertFalse(charge.is_refunded)

        charge.amount_refunded = 0
        charge.stripe_refund_id = ""
        charge.save()

        # refund - passes
        with mock.patch("aa_stripe.signals.stripe_charge_refunded.send") as refund_signal_send:
            charge.refund()
            refund_create_mocked.assert_called_with(
                charge=charge.stripe_charge_id, amount=charge.amount,
                idempotency_key="{}-{}".format(idempotency_key_prefix, charge.amount)
            )
            self.assertTrue(charge.is_refunded)
            self.assertEqual(charge.stripe_refund_id, "R1")
            self.assertEqual(charge.amount_refunded, charge.amount)
            refund_signal_send.assert_called_with(sender=StripeCharge, instance=charge)

        # refund - error: already refunded
        with self.assertRaises(StripeMethodNotAllowed):
            charge.refund()
            self.assertTrue(charge.is_refunded)
