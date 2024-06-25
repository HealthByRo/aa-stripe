import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class TestUser(AbstractUser):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
