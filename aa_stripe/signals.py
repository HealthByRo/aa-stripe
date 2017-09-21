# -*- coding: utf-8 -*-
import django.dispatch

charge_completed = django.dispatch.Signal(providing_args=["instance"])
