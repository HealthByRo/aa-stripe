from django.utils.translation import ugettext_lazy as _


class StripeMethodNotAllowed(Exception):
    details = _("Already created at stripe")


class StripeWebhookAlreadyParsed(Exception):
    details = _("This webhook has already been parsed")


class StripeWebhookParseError(Exception):
    details = _("Unable to parse webhook")


class StripeCouponAlreadyExists(Exception):
    details = _("Coupon with this coupon_id and creation date already exists")


class StripeInternalError(Exception):
    details = _("Temporary Stripe API error")
