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

import logging


class LoggerWrapper(logging.Logger):
    """
    Custom database logger wrapper. This adds custom functionality to select
    logging methods while preserving all other methods.

    """

    def __init__(self, baseLogger):
        """
        Initialize with the input baseLogger (the call to logging.getLogger()).

        """

        self.__class__ = type(
            baseLogger.__class__.__name__,
            (self.__class__, baseLogger.__class__),
            {},
        )
        self.__dict__ = baseLogger.__dict__

    def debug(self, *args, function=None, user_id=None, **kwargs):
        """Call debug() after adding stock 'extra' parameters."""

        super().debug(
            *args,
            **kwargs,
            extra={"function": function, "user_id": user_id},
        )

    def info(self, *args, function=None, user_id=None, **kwargs):
        """Call info() after adding stock 'extra' parameters."""

        super().info(
            *args,
            **kwargs,
            extra={"function": function, "user_id": user_id},
        )

    def warning(self, *args, function=None, user_id=None, **kwargs):
        """Call warning() after adding stock 'extra' parameters."""

        super().warning(
            *args,
            **kwargs,
            extra={"function": function, "user_id": user_id},
        )

    def error(self, *args, function=None, user_id=None, **kwargs):
        """Call error() after adding stock 'extra' parameters."""

        super().error(
            *args,
            **kwargs,
            extra={"function": function, "user_id": user_id},
        )

    def critical(self, *args, function=None, user_id=None, **kwargs):
        """Call critical() after adding stock 'extra' parameters."""

        super().critical(
            *args,
            **kwargs,
            extra={"function": function, "user_id": user_id},
        )
