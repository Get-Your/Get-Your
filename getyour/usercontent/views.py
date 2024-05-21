import logging

from django.shortcuts import render

from logger.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


def view_file(request):
    log.debug(
        "Entering function",
        function='view_file',
    )
    
    return render(
        request,
        'view_file.html',
        {
            'blob_data': request.session['blob_data'],
            'content_type': request.session['content_type'],
        },
        # # Set the redirect status
        # status=302,
    )
