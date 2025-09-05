from rodeo_utils.audit_log.django import Action, Display
from rodeo_utils.audit_log.tooling.types import RouteDetails

ROUTE_MAP = {
    "POST ^api/aa-stripe/customers$": RouteDetails(
        message="Stripe customer Created",
        action=Action.CREATE,
        type_display=Display.Order_Record,
    ),
    "GET ^api/aa-stripe/customers/(?P<stripe_customer_id>[\w\-]+)$": RouteDetails(
        message="Retrieve stripe customer details",
        action=Action.VIEW,
        type_display=Display.Order_Record,
    ),
    "POST ^api/aa-stripe/webhooks$": RouteDetails(
        message="Stripe event created",
        action=Action.CREATE,
        type_display=Display.Order_Record,
    ),
}
