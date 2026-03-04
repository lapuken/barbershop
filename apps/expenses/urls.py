from django.urls import path

from apps.expenses import views

app_name = "expenses"

urlpatterns = [
    path("", views.ExpenseListView.as_view(), name="list"),
    path("new/", views.ExpenseCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="delete"),
]
