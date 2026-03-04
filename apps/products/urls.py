from django.urls import path

from apps.products import views

app_name = "products"

urlpatterns = [
    path("", views.ProductListView.as_view(), name="list"),
    path("new/", views.ProductCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ProductUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ProductDeleteView.as_view(), name="delete"),
]
