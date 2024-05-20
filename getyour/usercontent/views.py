from django.shortcuts import render


def view_file(request):
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
