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
    
    return render(
        request,
        'view_blob.html',
        {
            'blob_data': request.session['blob_data'],
            'content_type': request.session['content_type'],
        },
        # # Set the redirect status
        # status=302,
    )
