from requests.packages.urllib3.util.retry import Retry


class LogRetry(Retry):
    """
    Adding extra logs before making a retry request     
    """

    def __init__(self, *args, function, logger=None, **kwargs):
        self.logger = logger
        self.function = function
        self.url = ''
        if 'url' in kwargs:
            self.url = kwargs['url']

        if self.logger:
            self.logger.debug(
                "Running URL request...",
                function=self.function,
            )
        super().__init__(*args, **kwargs)

    def increment(self, *args, **kwargs):
        incr = super().increment(*args, **kwargs)
        if self.logger:
            self.logger.debug(
                # "Incremented Retry for url='%s': %s",
                "Incremented Retry for url='%s'",
                self.url,
                # incr.new_retry,
                function=self.function,
            )
        return incr

    def new(self, **kwargs):
        return super().new(
            function=self.function,
            logger=self.logger,
            **kwargs,
        )