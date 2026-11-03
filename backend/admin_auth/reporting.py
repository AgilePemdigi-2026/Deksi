from django.views.debug import SafeExceptionReporterFilter


class AuthExceptionReporterFilter(SafeExceptionReporterFilter):
    """JSON credentials can appear in third-party stack locals, not only request.POST."""

    def get_traceback_frame_variables(self, request, tb_frame):
        return [(name, self.cleansed_substitute) for name in tb_frame.f_locals]


class AuthReportingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith("/api/auth/") or request.path_info == "/admin/login/":
            request.exception_reporter_filter = AuthExceptionReporterFilter()
            request.sensitive_post_parameters = "__ALL__"
        return self.get_response(request)
