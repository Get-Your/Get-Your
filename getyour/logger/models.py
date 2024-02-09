from django.db import models

from logger.constants import LOG_LEVELS


class LevelRD(models.Model):
    name = models.CharField(max_length=20)
    level = models.PositiveSmallIntegerField(primary_key=True)


class Detail(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at',
    )

    process_id = models.CharField(max_length=100, db_index=True)
    thread_id = models.CharField(max_length=100, db_index=True)

    app_name = models.CharField(max_length=20, db_index=True)
    logger_name = models.CharField(max_length=100)
    log_level = models.PositiveSmallIntegerField(
        choices=LOG_LEVELS,
    )
    function = models.CharField(max_length=50, null=True)
    user_id = models.PositiveBigIntegerField(null=True)

    message = models.TextField()
    trace = models.TextField(blank=True)

    # Create field that can be used to filter for not-yet-addressed records
    has_been_addressed = models.BooleanField(default=False, null=True)

    def __str__(self):
        return str(self.message)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = verbose_name = 'Logging'
        indexes = [
            models.Index(
                fields=['process_id', 'thread_id'],
                name='logger_det_process_712f94_idx',
            ),
        ]
