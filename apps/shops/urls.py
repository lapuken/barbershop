from django.urls import path

from apps.shops import views

app_name = "shops"

urlpatterns = [
    path("", views.ShopListView.as_view(), name="list"),
    path("new/", views.ShopCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ShopUpdateView.as_view(), name="edit"),
]
