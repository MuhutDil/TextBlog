from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class CustomUser(AbstractUser):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)

    def get_absolute_url(self):
        return reverse(
            "blog:user_detail",
            args=[
                self.username,
            ],
        )

    def __str__(self):
        return self.username
