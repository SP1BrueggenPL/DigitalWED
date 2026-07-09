from django.shortcuts import redirect
from django.urls import reverse


EXEMPT_URLS = {
    '/login/',
    '/logout/',
    '/zmien-haslo/',
}


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.path not in EXEMPT_URLS
            and not request.path.startswith('/static/')
            and not request.path.startswith('/admin/')
        ):
            try:
                if request.user.profile.must_change_password:
                    return redirect(reverse('zmien_haslo'))
            except Exception:
                pass

        return self.get_response(request)
