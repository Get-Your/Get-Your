"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from django.db import models

from get_your.constants import LOG_LEVELS


class LogLevel(models.Model):
    name = models.CharField(max_length=20)
    level = models.PositiveSmallIntegerField(primary_key=True)


class LogDetail(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created at",
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

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = verbose_name = "Logging"
        indexes = [
            models.Index(
                fields=["process_id", "thread_id"],
            ),
        ]

    def __str__(self):
        return str(self.message)
