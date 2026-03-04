from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("shops/", include("apps.shops.urls")),
    path("barbers/", include("apps.barbers.urls")),
    path("products/", include("apps.products.urls")),
    path("sales/", include("apps.sales.urls")),
    path("expenses/", include("apps.expenses.urls")),
    path("appointments/", include("apps.appointments.urls")),
    path("reports/", include("apps.reports.urls")),
    path("audit/", include("apps.audit.urls")),
    path("api/", include("apps.core.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
