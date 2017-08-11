=========
aa-stripe
=========
|travis|_ |pypi|_ |coveralls|_ |requiresio|_

Stripe integration for Django-based projects

This project's target is to make the Stripe API easier to use in Django-based applications.
At the moment the library supports:

* charging users
* plans
* subscriptions
* webhooks

Installation
============
Add ``aa_stripe`` to your app's ``INSTALLED_APPS``, and also set ``STRIPE_API_KEY`` in project settings. After all please migrate the app (``./manage.py migrate aa_stripe``).
Add ``STRIPE_WEBHOOK_ENDPOINT_SECRET`` into your settings from stripe webhooks configuration to enable webhooks.
Add ``STRIPE_USER_MODEL`` if it is different than settings.AUTH_USER_MODEL. In example when CC is connected to office not person. ``STRIPE_USER_MODEL`` defaults to AUTH_USER_MODEL.

Add ``aa_stripe.api_urls`` into your url conf.


Usage
=====


Creating a token for user
-------------------------
Use stripe.js (https://stripe.com/docs/stripe.js) to get single use token (stripe.js->createToken) and send it to API using ``/aa-stripe/customers`` to create Customer for the user. It runs:

::

    customer = stripe.Customer.create(source=data["id"]) # data is the response dictionary from Stripe API (in front-end)
    token = StripeToken.objects.create(user=request.user, content=data,
                                     customer_id=customer["id"])

This endpoint requires authenticated user. In case you need diferent implementation (like one call with register) you'll have to adjust your code.

Charging
--------
First of all, make sure to obtain Stripe user token from the Stripe API, and then save it to ``aa_stripe.models.StripeToken``, for example:
::

  import stripe
  from aa_stripe.models import StripeToken

  customer = stripe.Customer.create(source=data["id"]) # data is the response dictionary from Stripe API (in front-end)
  token = StripeToken.objects.create(user=request.user, content=data,
                                     customer_id=customer["id"])
  
To charge users, create an instance of ``aa_stripe.models.StripeCharge`` model and then call the ``charge()`` method:
::

  c = StripeCharge.objects.create(user=user, token=token, amount=500,  # in cents
                                  description="Charge for stuff",  # sent to Stripe
                                  comment="Comment for internal information")
  c.charge()

There is also a management command called ``charge_stripe`` in case
you need to process all the remaining charges.

Subscriptions support
---------------------
With Stripe user token already obtained you can create subscription.
::

  import stripe
  from aa_stripe.models import StripeSubscription

  subscription = StripeSubscription.objects.create(
    customer=self.customer,
    user=self.user,
    plan=self.plan,
    metadata={"name": "test subscription"},
  )

The newly created object is not sent to Stripe just yet.
::

  subscription_data = subscription.create_at_stripe()

The command above returns whole subscription data send by stripe, including, in example, discounts.

https://stripe.com/docs/api#subscriptions

Utility functions for subscriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* subscription.refresh_from_stripe() - gets updated subscription data from Stripe. Example usage: parsing webhooks - when webhook altering subscription is received it is good practice to verify the subscription at Stripe before making any actions.
* subscription.cancel() - cancels subscription at Stripe.
* StripeSubscription.get_subcriptions_for_cancel() - returns all subscriptions that should be canceled. Stripe does not support end date for subscription so it is up the user to implement expiration mechanism. Subscription has end_date that can be used for that.
* StripeSubscription.end_subscriptions() - cancels all subscriptions on Stripe that has passed end date. Use with caution, check internal comments.
* management command: end_subscription.py. Terminates outdated subscriptions in a safe way. In case of error returns it at the end, using Sentry if available or in console. Should be used in cron script.

Subscription Plans
------------------
Subscription Plans can be created using Stripe UI however there are cases when those needs to be created using API.
::

  import stripe
  from aa_stripe.models import StripeSubscriptionPlan

  plan = StripeSubscriptionPlan.objects.create(
    source={"a": "b"},
    amount=5000,
    name="gold-basic",
    interval=StripeSubscriptionPlan.INTERVAL_MONTH,
    interval_count=3,
  )

As with Subscription, the object has to be sent to stripe.
::

  plan_data = plan.create_at_stripe()

The command above returns whole plan data send by stripe.

https://stripe.com/docs/api#plans


Webhooks support
----------------
All webhooks should be sent to ``/aa-stripe/webhooks`` url. Add ``STRIPE_WEBHOOK_ENDPOINT_SECRET`` to your settings to enable webhook verifications. Each received webhook is saved as StripeWebhook object in database. User need to add parsing webhooks depending on the project.
Be advised. There might be times that Webhooks will not arrive because of some error or arrive in incorrect order. When parsing webhook it is also good to download the refered object to verify it's state.

Support
=======
* Django 1.11
* Python 2.7, 3.4-3.6

.. |travis| image:: https://secure.travis-ci.org/ArabellaTech/aa-stripe.svg?branch=master
.. _travis: http://travis-ci.org/ArabellaTech/aa-stripe

.. |pypi| image:: https://img.shields.io/pypi/v/aa-stripe.svg
.. _pypi: https://pypi.python.org/pypi/aa-stripe

.. |coveralls| image:: https://coveralls.io/repos/github/ArabellaTech/aa-stripe/badge.svg?branch=master
.. _coveralls: https://coveralls.io/github/ArabellaTech/aa-stripe

.. |requiresio| image:: https://requires.io/github/ArabellaTech/aa-stripe/requirements.svg?branch=master
.. _requiresio: https://requires.io/github/ArabellaTech/aa-stripe/requirements/
