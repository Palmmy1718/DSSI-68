from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    # ฟิลด์รับไฟล์สำหรับอัปโหลด (ไม่ผูกกับโมเดลโดยตรง)
    photo_file = forms.FileField(required=False, label='รูปพนักงาน')

    class Meta:
        model = Employee
        # ฟิลด์จริงตามโมเดล (ยกเว้น BLOB)
        fields = ['display_name', 'role_title', 'phone', 'is_active']
