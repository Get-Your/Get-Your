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

db_default_formatter = logging.Formatter()


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        # Import must be within the function for proper emitting
        from .models import LogDetail

        # Format trace, if exception exists
        trace = ""
        if record.exc_info:
            trace = db_default_formatter.formatException(record.exc_info)

        # Format the log message, based on the LOGGING 'formatters' in
        # common_settings
        msg = self.format(record)

        # Add stock 'extra' parameters if they don't exist
        if not hasattr(record, "user_id"):
            record.user_id = None
        if not hasattr(record, "function"):
            record.function = None

        kwargs = {
            "user_id": record.user_id,
            "function": record.function,
            "process_id": record.process,
            "thread_id": record.thread,
            "app_name": record.name.split(".", 1)[0],
            "logger_name": record.name,
            "log_level": record.levelno,
            "message": msg,
            "trace": trace,
        }

        LogDetail.objects.create(**kwargs)

    def format(self, record):
        fmt = self.formatter or db_default_formatter

        if isinstance(fmt, logging.Formatter):
            record.message = record.getMessage()

            # ignore exception traceback and stack info

            return fmt.formatMessage(record)
        return fmt.format(record)
