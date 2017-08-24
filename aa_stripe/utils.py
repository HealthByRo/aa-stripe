from datetime import datetime

from django.utils import timezone


def timestamp_to_timezone_aware_date(timestamp):
    return timezone.make_aware(datetime.fromtimestamp(timestamp))
