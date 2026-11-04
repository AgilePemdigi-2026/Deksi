"""Read-only request journal for owned Django LiveServer; no payloads/cookies recorded."""
import threading
from django.db import connection

entries = []
lock = threading.Lock()


class RequestJournal:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        with connection.cursor() as cursor:
            database_list = cursor.execute("PRAGMA database_list").fetchall()
        with lock:
            entries.append({"method": request.method, "path": request.path,
                            "query": request.GET.urlencode() if request.method == "GET" else "",
                            "status": response.status_code,
                            "database_list": database_list,
                            "configured_database": str(connection.settings_dict["NAME"])})
        return response
