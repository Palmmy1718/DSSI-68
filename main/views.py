# ---------------------- 1. IMPORTS (ต้องอยู่บนสุด) ----------------------

import logging
import base64
import os
import google.generativeai as genai
from django.conf import settings
from datetime import datetime, timedelta, date, time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bs4 import BeautifulSoup


from .forms import EmployeeForm
from .models import Employee, AppointmentSlot, Booking, Massage, GalleryImage, Promotion

logger = logging.getLogger(__name__)

# ---------------------- GEMINI UTILITY FUNCTION ----------------------
def ask_gemini(prompt: str) -> str:
    api_key = (
        getattr(settings, "GEMINI_API_KEY", "") 
        or os.getenv("GEMINI_API_KEY", "") 
        or os.getenv("GOOGLE_API_KEY", "")
    )
    if not api_key:
        return "ยังไม่ได้ตั้งค่า GEMINI_API_KEY/GOOGLE_API_KEY ใน .env"

    genai.configure(api_key=api_key)

    model_name = getattr(settings, "GEMINI_MODEL_NAME", "") or os.getenv(
        "GEMINI_MODEL_NAME", "gemini-2.0-flash-lite-latest"
    )
    model = genai.GenerativeModel(model_name)

    resp = model.generate_content(prompt)
    return getattr(resp, "text", "") or str(resp)

# ---------------------- 2. ADMIN VIEWS (MASSAGE) ----------------------

@login_required
def massage_admin_view(request):
    """หน้าหลักจัดการรายการนวด (แสดงรายการ + เพิ่มรายการ)"""
    add_mode = request.GET.get('add') == '1'
    if add_mode and request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        # รับไฟล์รูปภาพ
        image_file = request.FILES.get('image')

        if not name:
            messages.error(request, 'กรุณากรอกชื่อบริการนวด')
        else:
            try:
                m = Massage(
                    name=name,
                    description=description or '',
                    price=0,       # Default
                    duration=60,   # Default
                    image=image_file
                )
                m.save()
                messages.success(request, 'เพิ่มรายการนวดเรียบร้อย')
                return redirect('massage_admin')
            except Exception as e:
                messages.error(request, f'บันทึกไม่สำเร็จ: {e}')

    massages = Massage.objects.all().order_by('name')
    return render(request, 'main/massage_admin.html', {
        'massages': massages,
        'add_mode': add_mode,
    })

# --- [เพิ่มใหม่] ฟังก์ชันแก้ไขรายการนวด ---
@login_required
def massage_edit(request, pk):
    m = get_object_or_404(Massage, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        image_file = request.FILES.get('image')

        if not name:
            messages.error(request, 'กรุณากรอกชื่อ')
        else:
            try:
                m.name = name
                m.description = description
                # อัปเดตรูปเฉพาะเมื่อมีการอัปโหลดใหม่
                if image_file:
                    m.image = image_file
                
                m.save()
                messages.success(request, 'แก้ไขข้อมูลเรียบร้อย')
                return redirect('massage_admin')
            except Exception as e:
                messages.error(request, f'บันทึกไม่สำเร็จ: {e}')

    # ใช้หน้าเดิมแต่เปิดโหมดแก้ไข (edit_mode)
    massages = Massage.objects.all().order_by('name')
    return render(request, 'main/massage_admin.html', {
        'massages': massages,
        'edit_mode': True,     # บอก HTML ว่ากำลังแก้ไข
        'massage_obj': m       # ส่งข้อมูลเก่าไปโชว์
    })

# --- [เพิ่มใหม่] ฟังก์ชันลบรายการนวด ---
@login_required
def massage_delete(request, pk):
    m = get_object_or_404(Massage, pk=pk)
    m.delete()
    messages.success(request, 'ลบรายการเรียบร้อย')
    return redirect('massage_admin')


# ---------------------- 3. UTILITY FUNCTIONS ----------------------

def load_service_data():
    try:
        html_path = os.path.join(settings.BASE_DIR, "main", "templates", "Price.html")
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        text = soup.get_text(separator="\n")
        cleaned = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        return cleaned
    except Exception as e:
        return f"(ไม่สามารถโหลดข้อมูลราคาได้: {e})"

def _photo_url(emp: Employee):
    data = getattr(emp, 'photo_data', None)
    if data:
        mime = emp.photo_mime or 'image/jpeg'
        b64 = base64.b64encode(data).decode('ascii')
        return f"data:{mime};base64,{b64}"
    return None

def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
    return redirect('login')


# ---------------------- 4. FRONTEND PAGES ----------------------

def site_home(request):
    employees = Employee.objects.all().order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'home.html', {'employees': employees})

def site_massages(request):
    massages = Massage.objects.all().order_by('name')
    return render(request, 'Massages.html', {'massages': massages})

def site_price(request):
    return render(request, 'Price.html')

def site_team(request):
    employees = Employee.objects.all().order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'team.html', {'employees': employees})

def site_promotion(request):
    return render(request, 'Promotion.html')

def site_gallery(request):
    images = GalleryImage.objects.order_by('-created_at')
    return render(request, 'Gallery.html', {'images': images})

def contact(request):
    return render(request, 'contact.html')


# ---------------------- 5. BOOKING FLOW (REMOVED) ----------------------
# ส่วนนี้ถูกลบออกตามคำขอ (book_online, select_massage_view ฯลฯ)
# เพื่อป้องกัน Error และทำความสะอาดโค้ด


# ---------------------- 6. CALENDAR & SLOTS API ----------------------

def employee_calendar(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.photo_url = _photo_url(emp)
    return render(request, 'employee_calendar.html', {'emp': emp})

def employee_events(request, pk):
    emp = get_object_or_404(Employee, pk=pk, is_active=True)
    qs = emp.slots.all()
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        try:
            sdate = parse_date(start)
            qs = qs.filter(date__gte=sdate)
        except Exception: pass
    if end:
        try:
            edate = parse_date(end)
            qs = qs.filter(date__lte=edate)
        except Exception: pass

    events = []
    for slot in qs:
        start_dt = datetime.combine(slot.date, slot.start_time)
        end_dt = start_dt + timedelta(minutes=slot.duration_minutes or 60)
        events.append({
            "id": slot.id,
            "title": f"{slot.start_time.strftime('%H:%M')} {'(จองแล้ว)' if slot.is_booked else ''}",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "booked": slot.is_booked,
            "color": "#f87171" if slot.is_booked else "#22c55e",
        })
    return JsonResponse(events, safe=False, json_dumps_params={'ensure_ascii': False})

def employee_day_slots(request, pk, date):
    emp = get_object_or_404(Employee, pk=pk, is_active=True)
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "invalid date"}, status=400)
    slots = AppointmentSlot.objects.filter(employee=emp, date=day).order_by("start_time")
    data = [{
        "id": s.id,
        "time": s.start_time.strftime("%H:%M"),
        "is_booked": s.is_booked,
        "duration": s.duration_minutes or 60
    } for s in slots]
    return JsonResponse(
        {"employee": emp.display_name, "date": day.isoformat(), "slots": data},
        json_dumps_params={"ensure_ascii": False}
    )


# ---------------------- 7. ADMIN DASHBOARD & EMPLOYEE CRUD ----------------------

@login_required
def admin_dashboard(request):
    return redirect('employee_list')

@login_required
def employee_list(request):
    employees = Employee.objects.order_by('-id')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'main/employee_list.html', {'employees': employees})

@staff_required
def employee_add(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            emp = form.save(commit=False)
            f = request.FILES.get('photo_file')
            if f:
                emp.photo_mime = getattr(f, 'content_type', 'image/jpeg') or 'image/jpeg'
                emp.photo_data = f.read()
            emp.save()
            messages.success(request, 'เพิ่มพนักงานแล้ว')
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'main/employee_form.html', {'form': form, 'title': 'เพิ่มพนักงาน', 'photo_url': None})

# ---------------------- 8. GALLERY CRUD ----------------------

@login_required
def gallery_list(request):
    gallery = GalleryImage.objects.order_by('-created_at')
    return render(request, 'main/gallery_list.html', {'gallery': gallery})

@login_required
def gallery_add(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if not image_file:
            messages.error(request, 'กรุณาอัปโหลดรูปภาพ')
        else:
            try:
                g = GalleryImage(image=image_file)
                g.save()
                messages.success(request, 'เพิ่มรูปภาพสำเร็จ')
                return redirect('gallery_crud')
            except Exception as e:
                messages.error(request, f'บันทึกล้มเหลว: {e}')
    return render(request, 'main/gallery_form.html')

@login_required
def gallery_edit(request, pk):
    g = get_object_or_404(GalleryImage, pk=pk)
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if image_file:
            g.image = image_file
        title = request.POST.get('title')
        if title is not None:
            g.title = title
        try:
            g.save()
            messages.success(request, 'แก้ไขรูปภาพสำเร็จ')
            return redirect('gallery_crud')
        except Exception as e:
            messages.error(request, f'บันทึกล้มเหลว: {e}')
    # ใช้ฟอร์มเดียวกับ add เพื่อความง่าย หรือสร้างเทมเพลตใหม่ภายหลัง
    return render(request, 'main/gallery_form.html', {'item': g})

@login_required
@require_POST
def gallery_delete(request, pk):
    g = get_object_or_404(GalleryImage, pk=pk)
    g.delete()
    messages.success(request, 'ลบรูปภาพแล้ว')
    return redirect('gallery_crud')

@staff_required
def employee_edit(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            emp = form.save(commit=False)
            f = request.FILES.get('photo_file')
            if f:
                emp.photo_mime = getattr(f, 'content_type', 'image/jpeg') or 'image/jpeg'
                emp.photo_data = f.read()
            emp.save()
            messages.success(request, 'อัปเดตข้อมูลแล้ว')
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'main/employee_form.html', {'form': form, 'title': f'แก้ไข: {emp.display_name}', 'photo_url': _photo_url(emp)})

@staff_required
def employee_delete_view(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp.delete()
        messages.success(request, 'ลบพนักงานแล้ว')
        return redirect('employee_list')
    return render(request, 'main/employee_confirm_delete.html', {'employee': emp})

@staff_required
@require_POST
def employee_quick_rename(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    new_name = request.POST.get('display_name', '').strip()
    if new_name:
        emp.display_name = new_name
        emp.save(update_fields=['display_name'])
        messages.success(request, 'อัปเดตชื่อแล้ว')
    else:
        messages.error(request, 'ชื่อห้ามว่าง')
    return redirect('employee_list')

@staff_required
@require_POST
def employee_quick_photo(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    f = request.FILES.get('photo_file')
    if not f:
        messages.error(request, 'กรุณาเลือกไฟล์รูป')
        return redirect('employee_list')
    emp.photo_mime = getattr(f, 'content_type', 'image/jpeg') or 'image/jpeg'
    emp.photo_data = f.read()
    emp.save(update_fields=['photo_mime', 'photo_data'])
    messages.success(request, 'เปลี่ยนรูปแล้ว')
    return redirect('employee_list')

@staff_required
@require_POST
def employee_clear_photo(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.photo_data = None
    emp.photo_mime = None
    emp.save(update_fields=['photo_data', 'photo_mime'])
    messages.success(request, 'ลบรูปแล้ว')
    return redirect('employee_list')


# ---------------------- 8. AVAILABILITY MANAGEMENT ----------------------

@staff_required
def employee_availability(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            date_s = request.POST.get('date')
            start_s = request.POST.get('start_time')
            end_s = request.POST.get('end_time')
            try:
                date_obj = datetime.strptime(date_s, '%Y-%m-%d').date()
                start_obj = datetime.strptime(start_s, '%H:%M').time()
                end_obj = datetime.strptime(end_s, '%H:%M').time()
                start_dt = datetime.combine(date_obj, start_obj)
                end_dt = datetime.combine(date_obj, end_obj)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)
                duration = int((end_dt - start_dt).total_seconds() // 60)
                slot, created = AppointmentSlot.objects.get_or_create(
                    employee=emp, date=date_obj, start_time=start_obj,
                    defaults={'duration_minutes': duration}
                )
                if not created:
                    slot.duration_minutes = duration
                    slot.save(update_fields=['duration_minutes'])
                messages.success(request, 'เพิ่มเวลาว่างเรียบร้อย')
            except Exception:
                messages.error(request, 'ข้อมูลวันที่/เวลาไม่ถูกต้อง')
            return redirect('employee_availability', pk=pk)
        elif action == 'delete':
            slot_id = request.POST.get('slot_id')
            AppointmentSlot.objects.filter(pk=slot_id, employee=emp).delete()
            messages.success(request, 'ลบเวลาว่างแล้ว')
            return redirect('employee_availability', pk=pk)
    slots = emp.slots.order_by('date', 'start_time')
    return render(request, 'main/employee_time.html', {'employee': emp, 'slots': slots})

@login_required
def employee_availability_list(request):
    employees = Employee.objects.all().order_by('display_name')
    return render(request, 'main/employee_availability_list.html', {'employees': employees})

@login_required
def employee_availability_manage(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    slots = AppointmentSlot.objects.filter(employee=emp).order_by('date', 'start_time')
    if request.method == 'POST':
        date_str = request.POST.get('date')
        start_str = request.POST.get('start_time')
        end_str = request.POST.get('end_time')
        if not all([date_str, start_str, end_str]):
            messages.error(request, "กรุณากรอกข้อมูลให้ครบถ้วน")
            return redirect('employee_availability_manage', pk=pk)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()
            if start_time >= end_time:
                messages.error(request, "เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด")
                return redirect('employee_availability_manage', pk=pk)
            duration = int((datetime.combine(date, end_time) - datetime.combine(date, start_time)).total_seconds() // 60)
            overlap = AppointmentSlot.objects.filter(employee=emp, date=date, start_time=start_time).exists()
            if overlap:
                messages.error(request, "มีช่วงเวลานี้อยู่แล้ว กรุณาเลือกเวลาอื่น")
                return redirect('employee_availability_manage', pk=pk)
            AppointmentSlot.objects.create(employee=emp, date=date, start_time=start_time, duration_minutes=duration, is_booked=False)
            messages.success(request, "เพิ่มเวลาว่างเรียบร้อยแล้ว")
            return redirect('employee_availability_manage', pk=pk)
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect('employee_availability_manage', pk=pk)
    return render(request, 'main/employee_availability_manage.html', {'employee': emp, 'slots': slots})

@login_required
def employee_availability_delete(request, slot_id):
    slot = get_object_or_404(AppointmentSlot, pk=slot_id)
    emp_id = slot.employee.id
    slot.delete()
    messages.success(request, 'ลบเวลาว่างแล้ว')
    return redirect('employee_availability_manage', pk=emp_id)

@login_required
def availability_select(request):
    employees = Employee.objects.filter(is_active=True).order_by('display_name')
    return render(request, 'main/availability_select.html', {'employees': employees})


# ---------------------- 9. BOOKING SYSTEM & SLOTS ----------------------

TIME_SLOTS = [
    time(9,0), time(10,0), time(11,0), time(12,0),
    time(13,0), time(14,0), time(15,0), time(16,0),
    time(17,0), time(18,0), time(19,0),
]

def is_conflict(employee, date_obj, start_time, duration):
    end_time = (datetime.combine(date_obj, start_time) + timedelta(minutes=duration)).time()
    slots = AppointmentSlot.objects.filter(employee=employee, date=date_obj)
    for s in slots:
        s_end = (datetime.combine(s.date, s.start_time) + timedelta(minutes=s.duration_minutes)).time()
        if start_time < s_end and end_time > s.start_time:
            return True
    return False

def booking_slots(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    date_str = request.GET.get("date")
    duration = int(request.GET.get("duration", 60))
    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
         return JsonResponse({"error": "invalid date"}, status=400)
    slot_list = []
    for slot in TIME_SLOTS:
        start_dt = datetime.combine(date_obj, slot)
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.time()
        time_range = f"{slot.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
        conflict = is_conflict(employee, date_obj, slot, duration)
        slot_list.append({
            "time_range": time_range,
            "start_time": slot.strftime('%H:%M'),
            "available": not conflict
        })
    return render(request, "main/booking_slots.html", {
        "employee": employee,
        "date": date_str,
        "duration": duration,
        "slots": slot_list,
    })

def booking_form(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee")
        date_str = request.POST.get("date")
        duration = int(request.POST.get("duration", 60))
        times = request.POST.getlist("times")
        single_time = request.POST.get("time")
        if single_time and not times: times = [single_time]
        if not times:
            return render(request, "main/booking_result.html", {"success": False, "message": "กรุณาเลือกเวลาอย่างน้อย 1 ช่วง"})
        customer_name = request.POST.get("customer_name")
        customer_phone = request.POST.get("customer_phone")
        employee_obj = None
        if employee_id:
            try: employee_obj = Employee.objects.get(pk=employee_id)
            except Employee.DoesNotExist: pass
        if not customer_name or not customer_phone:
            return render(request, "main/booking_form.html", {
                "employee": employee_obj.display_name if employee_obj else employee_id,
                "employee_id": employee_id,
                "date": date_str,
                "duration": duration,
                "times": times,
                "error": None,
            })
        try: date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception: return render(request, "main/booking_result.html", {"success": False, "message": "รูปแบบวันที่ไม่ถูกต้อง"})
        if not employee_obj: return render(request, "main/booking_result.html", {"success": False, "message": "ไม่พบพนักงานที่เลือก"})
        created_count = 0
        conflicts = []
        for t in times:
            try: start_obj = datetime.strptime(t, "%H:%M").time()
            except ValueError:
                conflicts.append(f"รูปแบบเวลาไม่ถูกต้อง: {t}")
                continue
            if is_conflict(employee_obj, date_obj, start_obj, duration):
                conflicts.append(f"คิวไม่ว่างที่เวลา {t}")
                continue
            Booking.objects.create(
                employee=employee_obj,
                customer_name=customer_name,
                customer_phone=customer_phone,
                date=date_obj,
                start_time=start_obj,
                duration_minutes=duration,
            )
            created_count += 1
        if created_count == 0:
            return render(request, "main/booking_result.html", {"success": False, "message": "ไม่สามารถจองได้: " + "; ".join(conflicts)})
        msg = f"จองสำเร็จ {created_count} รายการ"
        if conflicts: msg += f" (บางรายการไม่ได้: {'; '.join(conflicts)})"
        return render(request, "main/booking_result.html", {"success": True, "message": msg})
    return redirect('home') # แก้ไขจาก select_massage เป็น home เพราะลบไปแล้ว

@require_POST
def book_slot(request, slot_id):
    slot = get_object_or_404(AppointmentSlot, pk=slot_id, is_booked=False)
    slot.is_booked = True
    slot.save(update_fields=['is_booked'])
    return JsonResponse({"success": True, "message": "จองสำเร็จแล้ว!"})


# ---------------------- 10. BOOKING LIST (ADMIN) ----------------------

@login_required
def booking_list(request):
    return admin_bookings_view(request)

@login_required
def admin_bookings_view(request):
    qs = Booking.objects.select_related("employee").order_by("date", "start_time")
    q_date = request.GET.get("date")
    if q_date:
        try:
            qd = datetime.strptime(q_date, "%Y-%m-%d").date()
            qs = qs.filter(date=qd)
        except Exception: pass
    return render(request, "main/admin_bookings.html", {
        "bookings": qs,
        "today": date.today(),
        "q_date": q_date or "",
    })

@login_required
@require_POST
def admin_booking_confirm(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.status = "confirmed"
    b.save()
    messages.success(request, "ยืนยันการจองเรียบร้อย")
    return redirect(request.POST.get("return") or "admin_bookings")

@login_required
@require_POST
def admin_booking_cancel(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.status = "cancelled"
    b.save()
    messages.success(request, "ยกเลิกการจองเรียบร้อย")
    return redirect(request.POST.get("return") or "admin_bookings")

@login_required
@require_POST
def admin_booking_delete(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.delete()
    messages.success(request, "ลบการจองแล้ว")
    return redirect(request.POST.get("return") or "admin_bookings")


# ---------------------- 11. AUTHENTICATION ----------------------

def register_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        if password != confirm:
            messages.error(request, "รหัสผ่านไม่ตรงกัน")
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, "ชื่อผู้ใช้นี้มีอยู่แล้ว")
            return redirect('register')
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "สมัครสมาชิกสำเร็จ! โปรดเข้าสู่ระบบ")
        return redirect('login')
    return render(request, 'register.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return render(request, "main/login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect("login")

def customer_register_view(request):
    storage = messages.get_messages(request)
    for _ in storage: pass
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        if password != confirm:
            messages.error(request, "รหัสผ่านไม่ตรงกัน")
            return redirect('customer_register')
        if User.objects.filter(username=username).exists():
            messages.error(request, "ชื่อผู้ใช้นี้มีอยู่แล้ว")
            return redirect('customer_register')
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "สมัครสมาชิกสำเร็จ! โปรดเข้าสู่ระบบ")
        return redirect('customer_login')
    return render(request, 'main/customer_register.html')

def customer_login_view(request):
    storage = messages.get_messages(request)
    for _ in storage: pass
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        User = get_user_model()
        user_objs = User.objects.filter(email=email)
        found = False
        for user_obj in user_objs:
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"ยินดีต้อนรับ {user_obj.username}!")
                return redirect('home')
                found = True
                break
        if not found:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    return render(request, 'main/customer_login.html')

def customer_logout_view(request):
    logout(request)
    messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect('customer_login')


# ---------------------- 12. GALLERY CRUD ----------------------

def gallery_list(request):
    gallery = GalleryImage.objects.all().order_by('-created_at')
    return render(request, 'main/gallery_list.html', {'gallery': gallery})

def gallery_add(request):
    if request.method == 'POST':
        title = request.POST.get('title', '')
        image = request.FILES.get('image')
        if image:
            GalleryImage.objects.create(title=title, image=image)
            return redirect('gallery_crud')
    return render(request, 'main/gallery_form.html')

def gallery_edit(request, pk):
    image = get_object_or_404(GalleryImage, pk=pk)
    if request.method == 'POST':
        image.title = request.POST.get('title', '')
        if 'image' in request.FILES:
            image.image = request.FILES['image']
        image.save()
        return redirect('gallery_crud')
    return render(request, 'main/gallery_form.html', {'image': image})

def gallery_delete(request, pk):
    image = get_object_or_404(GalleryImage, pk=pk)
    image.delete()
    return redirect('gallery_crud')


# ---------------------- 13. AI CHAT & GEMINI ----------------------
import google.generativeai as genai

def _get_gemini_model():
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return None, "ยังไม่ได้ตั้งค่า GEMINI_API_KEY/GOOGLE_API_KEY ใน .env"

    model_name = getattr(settings, "GEMINI_MODEL_NAME", "") or os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-lite-latest")

    # configure ครั้งเดียวต่อ request ก็พอ (ง่าย/ชัวร์)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name), None

def ask_gemini(prompt: str) -> str:
    model, err = _get_gemini_model()
    if err:
        return err
    resp = model.generate_content(prompt)
    return getattr(resp, "text", "") or str(resp)

@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    user_message = request.POST.get("message", "").strip()
    if not user_message:
        return JsonResponse({"error": "ข้อความว่าง"}, status=400)

    service_info = load_service_data()

    promo_keywords = ["โปร", "promotion", "โปรโมชั่น", "โปรโมชัน", "ส่วนลด", "offer", "deal"]
    is_promo_question = any(word in user_message.lower() for word in promo_keywords)

    if is_promo_question:
        promos = Promotion.objects.filter(is_active=True).order_by("-updated_at")
        promo_text = "\n".join([f"- {p.title}: {p.description}" for p in promos]) if promos.exists() else "ขณะนี้ยังไม่มีโปรโมชั่นพิเศษค่ะ"
        final_prompt = f"""
คุณคือแชตบอทของร้าน Chokdee Thai Massage in Hévíz
ข้อมูลโปรโมชั่นปัจจุบัน:
{promo_text}
ลูกค้าถามว่า: "{user_message}"
กรุณาตอบสั้นๆ และสุภาพ
"""
    else:
        final_prompt = f"""
คุณคือแชตบอทของร้าน Chokdee Thai Massage in Hévíz
ข้อมูลบริการ:
{service_info}
ลูกค้าถามว่า: "{user_message}"
กรุณาตอบสั้นๆ และสุภาพ
"""

    try:
        reply = ask_gemini(final_prompt)
        return JsonResponse({"reply": reply}, json_dumps_params={"ensure_ascii": False})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def chat_ui(request):
    return render(request, "chat.html")

def list_models(request):
    return JsonResponse({"models": ["not-implemented"]})

def test_gemini(request):
    reply = ask_gemini("สวัสดีจาก Django!")
    return JsonResponse({"reply": reply}, json_dumps_params={"ensure_ascii": False})

