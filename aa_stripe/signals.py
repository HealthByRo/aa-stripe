def stripe_webhook_post_save(sender, instance, created, **kwargs):
    from aa_stripe.models import StripeCoupon

    if not created:
        return

    event_type = instance.raw_data.get("type")
    if event_type == "coupon.deleted":
        coupon_id = instance.raw_data["data"]["object"]["id"]
        StripeCoupon.objects.filter(coupon_id=coupon_id).update(is_deleted=True)
