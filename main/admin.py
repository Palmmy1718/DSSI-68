from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Employee,
    Massage,
    AppointmentSlot,
    GalleryImage,
    Service,
    Promotion,   # <<< เพิ่ม Promotion
)
from .forms import EmployeeForm


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeForm
    list_display = ("id", "display_name", "role_title", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("display_name", "role_title", "phone")
    list_display_links = ("id", "display_name")


# ---------------------- SERVICE ADMIN ----------------------
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price_30", "price_60", "price_90", "price_120")
    search_fields = ("name", "description")
    list_display_links = ("id", "name")
# -----------------------------------------------------------


# ---------------------- PROMOTION ADMIN ----------------------
@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "is_active", "updated_at")
    search_fields = ("title", "description")
    list_filter = ("is_active",)
    list_display_links = ("id", "title")
# -------------------------------------------------------------


@admin.register(Massage)
class MassageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "duration")
    search_fields = ("name", "description")
    list_filter = ("duration",)
    list_display_links = ("id", "name")


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "date", "start_time", "duration_minutes", "is_booked")
    list_filter = ("employee", "date", "is_booked")
    search_fields = ("employee__display_name",)


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("id", "preview", "title", "created_at")
    readonly_fields = ("preview",)
    search_fields = ("title",)
    list_display_links = ("id", "title")
    ordering = ("-created_at",)

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="70" style="object-fit:cover;border-radius:6px;">',
                obj.image.url
            )
        return "(ไม่มีรูป)"

    preview.short_description = "ภาพตัวอย่าง"
