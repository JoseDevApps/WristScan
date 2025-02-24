from django.urls import path

from . import views
app_name = 'dashboard'
urlpatterns = [
    path('', views.inicio, name="inicio"),
    path('qrgen', views.qrgen, name="qrgen"),
    path('qrscan', views.qrscan, name="qrscan"),
    path('create', views.create, name="create"),
    path('createdb', views.createdb, name="createdb"),
    path('assign', views.assign, name="assign"),
    # path('assign/<int:user_id>', views.update_user_email, name="assign"),
    path('update_user_email/<int:user_id>/', views.update_user_email, name='update_user_email'),
    path('update_event/<int:pk>/', views.updatedb, name='update_event'),
    path('share', views.share_qr_codes, name="share"),
    path('tables', views.listdb, name="tables"),
    path('create-checkout-session/<int:pk>/<int:slug>/', views.create_checkout_session, name='create_checkout_session'),
    path('cancel/', views.CancelView.as_view(), name='cancel'),
    path('success/', views.SuccessView.as_view(), name='success'),
]