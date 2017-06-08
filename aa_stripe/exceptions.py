from django.utils.translation import ugettext_lazy as _


class StripeMethodNotAllowed(Exception):
    details = _("Already created at stripe")
