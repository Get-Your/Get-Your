from django.db import models


class LevelRD(models.Model):
    name = models.CharField(max_length=20)
    level = models.PositiveSmallIntegerField(primary_key=True)


class Detail(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created at',
    )

    process_id = models.PositiveIntegerField()
    thread_id = models.PositiveIntegerField()

    app_name = models.CharField(max_length=20, db_index=True)
    logger_name = models.CharField(max_length=100)
    log_level = models.ForeignKey(
        LevelRD,
        related_name='detail',
        # Don't update these levels if the log_level is deleted
        on_delete=models.DO_NOTHING,
    )
    function = models.CharField(max_length=50, null=True)
    user_id = models.PositiveBigIntegerField(null=True)

    lineno = models.PositiveIntegerField()
    message = models.TextField()
    trace = models.TextField(blank=True)

    def __str__(self):
        return str(self.message)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = verbose_name = 'Logging'
        indexes = [
            models.Index(
                fields=['process_id', 'thread_id'],
                name='process_thread_idx',
            ),
        ]
