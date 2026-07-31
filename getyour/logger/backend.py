from requests.packages.urllib3.util.retry import Retry

from logger.constants import retry_strategy


class LogRetry(Retry):
    """
    Adding extra logs before making a retry request     
    """

    def __init__(self, *args, logger=None, function=None, **kwargs):
        self.logger = logger
        self.function = function
        super().__init__(*args, **kwargs)

    def increment(self, *args, **kwargs):
        incr = super().increment(*args, **kwargs)
        if self.logger:
            self.logger.debug(
                "Retrying %i (of up to %i)...",
                retry_strategy['total']-incr.total,
                retry_strategy['total'],
                function=self.function,
            )
        return incr

    def new(self, **kwargs):
        return super().new(
            logger=self.logger,
            function=self.function,
            **kwargs,
        )