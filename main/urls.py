from django.urls import path
from . import views

urlpatterns = [
    path('massage-admin/', views.massage_admin_view, name='massage_admin'),
    path('massages/<int:pk>/edit/', views.massage_edit, name='massage_edit'),
    path('massages/<int:pk>/delete/', views.massage_delete, name='massage_delete'),

    # ------------------ หน้าเว็บทั่วไป ------------------
    path('', views.site_home, name='home'),
    path('massages/', views.site_massages, name='massages'),
    path('price/', views.site_price, name='price'),
    path('team/', views.site_team, name='team'),
    path('promotion/', views.site_promotion, name='promotion'),
    path('gallery/', views.site_gallery, name='gallery'),
    path('contact/', views.contact, name='contact'),

    # ------------------ พนักงาน ------------------
    path('adminx/', views.admin_dashboard, name='admin_dashboard'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_add, name='employee_add'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete_view, name='employee_delete'),
    path('employees/<int:pk>/rename/', views.employee_quick_rename, name='employee_quick_rename'),
    path('employees/<int:pk>/photo/', views.employee_quick_photo, name='employee_quick_photo'),
    path('employees/<int:pk>/clear-photo/', views.employee_clear_photo, name='employee_clear_photo'),

    # ปฏิทิน
    path('employees/<int:pk>/calendar/', views.employee_calendar, name='employee_calendar'),
    path('employees/<int:pk>/events/', views.employee_events, name='employee_events'),
    path('employees/<int:pk>/slots/<str:date>/', views.employee_day_slots, name='employee_day_slots'),
    path('employees/<int:pk>/availability/', views.employee_availability, name='employee_availability'),

    # ------------------ คิวจอง ------------------
    path('bookings/', views.booking_list, name='booking_list'),
    # path('book-online/', views.book_online, name='book_online'),  <-- ลบออกแล้ว
    path('bookings/admin/', views.admin_bookings_view, name='admin_bookings'),
    path('bookings/admin/<int:pk>/delete/', views.admin_booking_delete, name='admin_booking_delete'),

    # ------------------ Gemini API ------------------
    path('list-models/', views.list_models, name='list_models'),
    path('test-gemini/', views.test_gemini, name='test_gemini'),

    # ------------------ แชท ------------------
    path('chat/', views.chat_api, name='chat_api'),
    path('chat-ui/', views.chat_ui, name='chat_ui'),

    # ------------------ ลูกค้า ------------------
    path('customer/register/', views.customer_register_view, name='customer_register'),
    path('customer/login/', views.customer_login_view, name='customer_login'),
    path('customer/logout/', views.customer_logout_view, name='customer_logout'),

    # แอดมิน login
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ------------------ Gallery CRUD ------------------
    path('galleryx/', views.gallery_list, name='gallery_crud'),
    path('galleryx/add/', views.gallery_add, name='gallery_add'),
    path('galleryx/<int:pk>/edit/', views.gallery_edit, name='gallery_edit'),
    path('galleryx/<int:pk>/delete/', views.gallery_delete, name='gallery_delete'),

    # ---- Employee Availability ----
    path('availability/', views.employee_availability_list, name='employee_availability_list'),
    path('availability/<int:pk>/', views.employee_availability_manage, name='employee_availability_manage'),
    path('availability/delete/<int:slot_id>/', views.employee_availability_delete, name='employee_availability_delete'),

    # ------------------ Public Booking ------------------
    path('booking-slots/<int:employee_id>/', views.booking_slots, name='booking_slots'),
    path('booking-form/', views.booking_form, name='booking_form'),
]