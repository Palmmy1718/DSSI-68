from django import template
from django.utils.translation import gettext as _

register = template.Library()

@register.filter
def translate_db(value):
    if not value:
        return ""
    # .strip() ช่วยตัดช่องว่างหน้า-หลัง และตัวขึ้นบรรทัดใหม่ส่วนเกินออก
    # ทำให้จับคู่กับไฟล์แปลภาษาได้แม่นยำขึ้น
    clean_value = str(value).strip() 
    return _(clean_value)