from django import forms
from .models import Employee, Promotion, Massage

class EmployeeForm(forms.ModelForm):
    # ฟิลด์รับไฟล์สำหรับอัปโหลด (ไม่ผูกกับโมเดลโดยตรง)
    photo_file = forms.FileField(required=False, label='รูปพนักงาน')

    class Meta:
        model = Employee
        # ฟิลด์จริงตามโมเดล (ยกเว้น BLOB)
        fields = ['display_name', 'role_title', 'phone', 'is_active']

class MassageForm(forms.ModelForm):
    class Meta:
        model = Massage
        fields = ['name', 'description', 'name_en', 'description_en', 'name_de', 'description_de', 'price', 'duration', 'image']

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['title', 'description', 'is_active']
