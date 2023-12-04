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

        self.__class__ = type(baseLogger.__class__.__name__,
                             (self.__class__, baseLogger.__class__),
                             {})
        self.__dict__ = baseLogger.__dict__

    def debug(self, *args, function=None, user_id=None, **kwargs):
        """ Call debug() after adding stock 'extra' parameters. """

        super().debug(
            *args,
            **kwargs,
            extra={'function': function, 'user_id': user_id},
        )

    def info(self, *args, function=None, user_id=None, **kwargs):
        """ Call info() after adding stock 'extra' parameters. """

        super().info(
            *args,
            **kwargs,
            extra={'function': function, 'user_id': user_id},
        )

    def warning(self, *args, function=None, user_id=None, **kwargs):
        """ Call warning() after adding stock 'extra' parameters. """

        super().warning(
            *args,
            **kwargs,
            extra={'function': function, 'user_id': user_id},
        )

    def error(self, *args, function=None, user_id=None, **kwargs):
        """ Call error() after adding stock 'extra' parameters. """

        super().error(
            *args,
            **kwargs,
            extra={'function': function, 'user_id': user_id},
        )

    def critical(self, *args, function=None, user_id=None, **kwargs):
        """ Call critical() after adding stock 'extra' parameters. """

        super().critical(
            *args,
            **kwargs,
            extra={'function': function, 'user_id': user_id},
        )
