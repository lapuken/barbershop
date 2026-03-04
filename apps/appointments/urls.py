from django.urls import path

from apps.appointments import views

app_name = "appointments"

urlpatterns = [
    path("", views.AppointmentListView.as_view(), name="list"),
    path("new/", views.AppointmentCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.AppointmentUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.AppointmentDeleteView.as_view(), name="delete"),
    path("customers/", views.CustomerListView.as_view(), name="customers"),
    path("customers/new/", views.CustomerCreateView.as_view(), name="customer-create"),
    path("customers/<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="customer-edit"),
    path("customers/<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="customer-delete"),
    path("availability/", views.PublicAvailabilityView.as_view(), name="public-availability"),
    path("book/", views.PublicBookingView.as_view(), name="public-book"),
    path("book/success/", views.PublicBookingSuccessView.as_view(), name="public-success"),
]
