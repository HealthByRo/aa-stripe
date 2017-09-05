from django.test import TestCase

from aa_stripe.settings import stripe_settings


class TestSettings(TestCase):
    def test_defaults(self):
        self.assertEqual(stripe_settings.PENDING_WEBHOOKS_THRESHOLD, 20)
