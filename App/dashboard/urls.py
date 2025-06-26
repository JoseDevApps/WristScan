from django.urls import path

from . import views
app_name = 'dashboard'
urlpatterns = [
    path('', views.inicio, name="inicio"),
    path('export_qr_summary/', views.export_qr_summary_to_excel, name="export_qr_summary"),
    # path('export_qr_codes/', views.export_qr_codes_to_excel, name="export_qr_codes"),
    path('export_qr_codes/<int:event_id>/', views.export_qr_codes_to_excel, name='export_qr_codes'),

    path('qrgen', views.qrgen, name="qrgen"),
    path('qrscan', views.qrscan, name="qrscan"),
    path('create', views.create, name="create"),
    path('createdb', views.createdb, name="createdb"),
    path('assign', views.assign, name="assign"),

    path('update_user_email/<int:user_id>/', views.update_user_email, name='update_user_email'),
    path('update_event/<int:pk>/', views.updatedb, name='update_event'),
    path('event/<int:event_id>/download_qr_zip/', views.download_qr_zip, name='download_qr_zip'),
    path('share', views.share_qr_codes, name="share"),
    path('tables', views.listdb, name="tables"),
    path('create-checkout-session/<int:pk>/', views.create_checkout_session, name='create_checkout_session'),
    path('cancel/', views.CancelView.as_view(), name='cancel'),
    path('success/', views.SuccessView.as_view(), name='success'),
    path('qrpass/', views.qr_app, name="qrpass"),
    path('logout/', views.force_logout_view, name='logout'),
    path('modal/', views.ShowModalView.as_view(), name="modal-form"),
]