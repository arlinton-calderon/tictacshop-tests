from django.urls import path

from frontend.views.index import IndexView

urlpatterns = [
    path('', IndexView.as_view())
]
