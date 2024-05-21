import logging

from django.shortcuts import render

from logger.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def view_blob(request):
    log.debug(
        "Entering function",
        function='view_blob',
    )
    
    response = render(
        request,
        'view_blob.html',
        {
            'blob_data': request.session['blob_data'],
            'content_type': request.session['blob_type'],
        },
        # # Set the redirect status
        # status=302,
    )

    # Delete the session vars just before serving the blob
    del request.session['blob_data']
    del request.session['blob_type']

    return response
