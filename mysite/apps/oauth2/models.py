from django.db import models


class Oauth2(models.Model):
    class Meta:
        db_table = "oauth2"
        verbose_name = "Oauth2"
        verbose_name_plural = verbose_name
