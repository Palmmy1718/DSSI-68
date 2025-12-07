from django.db import models

class Employee(models.Model):
    display_name = models.CharField(max_length=120)
    role_title = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    photo_mime = models.CharField(max_length=100, blank=True, null=True)
    photo_data = models.BinaryField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name


# ---------------------- SERVICE MODEL (เก่า) ----------------------
class Service(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_30 = models.IntegerField(blank=True, null=True)
    price_60 = models.IntegerField(blank=True, null=True)
    price_90 = models.IntegerField(blank=True, null=True)
    price_120 = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.name


# ---------------------- MASSAGE MODEL (ใช้งานจริง) ----------------------
class Massage(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # ปรับเป็น IntegerField และใส่ default เพื่อไม่ให้ Error
    price = models.IntegerField(default=0) 
    duration = models.IntegerField(default=60) 
    
    # [แก้ไขสำคัญ] เปลี่ยนเป็น ImageField เพื่อเก็บไฟล์รูป
    image = models.ImageField(upload_to='massage_images/', blank=True, null=True)

    def __str__(self):
        return self.name


class AppointmentSlot(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ('employee', 'date', 'start_time')

    def __str__(self):
        return f"{self.employee.display_name} - {self.date} {self.start_time}"


class GalleryImage(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"รูปที่ {self.id}"


class Promotion(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# ---------------------- BOOKING MODEL ----------------------
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'รออนุมัติ'),
        ('confirmed', 'ยืนยันแล้ว'),
        ('cancelled', 'ยกเลิกแล้ว'),
    )

    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    massage = models.ForeignKey(Massage, on_delete=models.CASCADE, null=True, blank=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=40)

    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.customer_name} - {self.date} {self.start_time}"