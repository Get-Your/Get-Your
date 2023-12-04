import logging


db_default_formatter = logging.Formatter()


class DatabaseLogHandler(logging.Handler):

    def emit(self, record):

        from log.models import Detail

        # Format trace, if exception exists
        trace = ''
        if record.exc_info:
            trace = db_default_formatter.formatException(record.exc_info)
            
        # Format the log message, based on the LOGGING 'formatters' in
        # common_settings
        msg = self.format(record)

        kwargs = {
            'process_id': record.process,
            'thread_id': record.thread,
            'app_name': record.name.split('.', 1)[0],
            'logger_name': record.name,
            'log_level': record.levelno,
            'lineno': record.lineno,
            'message': msg,
            'trace': trace
        }

        Detail.objects.create(**kwargs)

    def format(self, record):

        if self.formatter:
            fmt = self.formatter
        else:
            fmt = db_default_formatter

        if isinstance(fmt, logging.Formatter):
            record.message = record.getMessage()

            # ignore exception traceback and stack info

            return fmt.formatMessage(record)
        else:
            return fmt.format(record)