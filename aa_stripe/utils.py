from aa_stripe.models import StripeToken


def get_latest_active_token_for_user(user):
    """Returns last active stripe token for user"""
    token = StripeToken.objects.filter(user_id=user.id, is_active=True).last()
    return token
