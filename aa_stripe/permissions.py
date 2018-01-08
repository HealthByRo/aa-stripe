# -*- coding: utf-8 -*-
from rest_framework.permissions import BasePermission

from aa_stripe.models import StripeCustomer


class IsCardOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.customer == StripeCustomer.get_latest_active_customer_for_user(request.user)
