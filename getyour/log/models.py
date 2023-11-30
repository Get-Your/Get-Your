from django.db import models

from log.constants import LOG_LEVELS


class LevelRD(models.Model):
    name = models.CharField(max_length=20)
    level = models.PositiveSmallIntegerField(primary_key=True)


class Detail(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at',
    )
    logger_name = models.CharField(max_length=100)
    log_level = models.PositiveSmallIntegerField(
        choices=LOG_LEVELS,
        db_index=True,
    )
    message = models.TextField()
    trace = models.TextField(blank=True, null=True)

    def __str__(self):
        return str(self.message)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = verbose_name = 'Logging'
