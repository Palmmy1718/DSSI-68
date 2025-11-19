from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# เส้นทางสำหรับเปลี่ยนภาษา ผ่าน /i18n/setlang/
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

# เส้นทางหลักของเว็บ (รองรับ prefix ภาษา เช่น /de/, /en/)
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    prefix_default_language=False,   # ไม่เติม /th/ ให้ภาษา default
)

# Static & Media ไว้นอก i18n_patterns เสมอ
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
