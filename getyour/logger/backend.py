from requests.packages.urllib3.util.retry import Retry
from requests import Session


class LogRetry(Retry):
    """
    Adding extra logs before making a retry request     
    """

    def __init__(self, *args, logger_function, logger_obj=None, **kwargs):
        self.logger_obj = logger_obj
        self.logger_function = logger_function
        self.url = ''
        if 'url' in kwargs:
            self.url = kwargs['url']

        if self.logger_obj:
            self.logger_obj.debug(
                "Running URL request...",
                function=self.logger_function,
            )
        super().__init__(*args, **kwargs)

    def increment(self, *args, **kwargs):
        incr = super().increment(*args, **kwargs)
        if self.logger_obj:
            self.logger_obj.debug(
                # "Incremented Retry for url='%s': %s",
                "Incremented Retry for url='%s'",
                self.url,
                # incr.new_retry,
                function=self.logger_function,
            )
        return incr

    def new(self, **kwargs):
        return super().new(
            logger_function=self.logger_function,
            logger_obj=self.logger_obj,
            **kwargs,
        )