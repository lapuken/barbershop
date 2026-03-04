from django.urls import path

from apps.barbers import views

app_name = "barbers"

urlpatterns = [
    path("", views.BarberListView.as_view(), name="list"),
    path("new/", views.BarberCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.BarberUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.BarberDeleteView.as_view(), name="delete"),
]
