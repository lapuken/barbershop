from django.urls import path

from apps.sales import views

app_name = "sales"

urlpatterns = [
    path("", views.SaleListView.as_view(), name="list"),
    path("new/", views.SaleCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.SaleUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.SaleDeleteView.as_view(), name="delete"),
]
