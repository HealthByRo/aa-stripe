# -*- coding: utf-8 -*-
import django.dispatch

stripe_charge_succeeded = django.dispatch.Signal(providing_args=["instance"])
stripe_charge_card_exception = django.dispatch.Signal(providing_args=["instance", "exception"])
stripe_charge_refunded = django.dispatch.Signal(providing_args=["instance"])
