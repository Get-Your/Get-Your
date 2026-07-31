import logging

LOG_LEVELS = (
    (logging.NOTSET, 'NotSet'),
    (logging.INFO, 'Info'),
    (logging.WARNING, 'Warning'),
    (logging.DEBUG, 'Debug'),
    (logging.ERROR, 'Error'),
    (logging.FATAL, 'Fatal'),
)

# Set the API-call retry strategy dict
retry_strategy = {
    # Retry up to 5 times
    'total': 5,
    # Only retry twice for 'read' errors
    'read': 2,
    # Follow up to 10 redirects
    'redirect': 10,
    # Force 'bad' statuses to retry
    'status_forcelist': [502, 503, 504],
    # The factor to 'back off' at each retry (as a multiple of the retry
    # iteration), to a maximum overall
    'backoff_factor': 0.1,
    'backoff_max': 1,
}