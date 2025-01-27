from django.urls import path

from . import views
app_name = 'dashboard'
urlpatterns = [
    path('', views.inicio, name="inicio"),
    path('qrgen', views.qrgen, name="qrgen"),
    path('qrscan', views.qrscan, name="qrscan"),
    path('create', views.assign, name="create"),
    path('assign', views.basic, name="assign"),
    path('basic', views.tables, name="basic"),
    path('tables', views.qrgen, name="tables"),
]