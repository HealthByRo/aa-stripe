=========
aa-stripe
=========
|travis|_ |pypi|_ |coveralls|_ |requiresio|_

Stripe integration for Django-based projects

This project's target is to make the Stripe API easier to use in Django-based applications.
At the moment the library supports:

* charging users
* TODO: FIll information with usage examples about
** plans
** subscriptions
** webhooks

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

Webhooks support
----------------
All webhooks should be sent to ``/aa-stripe/webhooks`` url. Add ``STRIPE_WEBHOOK_ENDPOINT_SECRET`` to your settings to enable webhook verifications. Each received webhook is saved as StripeWebhook object in database. User need to add parsing webhooks depending on the project.

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
