import logging

from django.shortcuts import render
from django.conf import settings

from logger.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def view_blob(request):
    log.info(
        "Loading blob viewer{}".format(
            # Add the code version to the log message, if it exists
            f" (running {settings.CODE_VERSION})" if settings.CODE_VERSION!='' else '',
        ),
        function='view_blob',
    )
    
    response = render(
        request,
        'view_blob.html',
        {
            'blob_data': request.session['blob_data'],
            'content_type': request.session['blob_type'],
        },
    )

    # Delete the session vars just before serving the blob
    del request.session['blob_data']
    del request.session['blob_type']

    return response
