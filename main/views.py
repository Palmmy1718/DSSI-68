def massage_admin_view(request):
    return render(request, 'main/massage_admin.html')
# main/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from .forms import EmployeeForm
from .models import Employee, AppointmentSlot, Booking
import base64
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------- LOAD SERVICE DATA ----------------------
from bs4 import BeautifulSoup

def load_service_data():
    """อ่านข้อมูลบริการจากไฟล์ HTML แล้วแปลงเป็นข้อความให้อ่านง่าย"""
    try:
        html_path = os.path.join(settings.BASE_DIR, "main", "templates", "Price.html")
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # ดึงแต่ตัวอักษรจาก HTML
        text = soup.get_text(separator="\n")
        cleaned = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        return cleaned

    except Exception as e:
        return f"(ไม่สามารถโหลดข้อมูลราคาได้: {e})"

# ---------------------- FRONTEND PAGES ----------------------

def site_home(request):
    employees = Employee.objects.all().order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'home.html', {'employees': employees})


def employee_calendar(request, pk):
    """Render the employee calendar page (FullCalendar)."""
    emp = get_object_or_404(Employee, pk=pk)
    emp.photo_url = _photo_url(emp)
    # Template file is located at main/templates/employee_calendar.html (root of app templates)
    return render(request, 'employee_calendar.html', {'emp': emp})


def employee_events(request, pk):
    """Return JSON data for FullCalendar events."""
    emp = get_object_or_404(Employee, pk=pk, is_active=True)
    qs = emp.slots.all()

    # Filter by start/end range (sent by FullCalendar)
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        try:
            sdate = parse_date(start)
            qs = qs.filter(date__gte=sdate)
        except Exception:
            pass
    if end:
        try:
            edate = parse_date(end)
            qs = qs.filter(date__lte=edate)
        except Exception:
            pass

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
            "color": "#f87171" if slot.is_booked else "#22c55e",  # แดงถ้าจองแล้ว เขียวถ้ายังว่าง
        })

    return JsonResponse(events, safe=False, json_dumps_params={'ensure_ascii': False})


def employee_day_slots(request, pk, date):
    """
    เมื่อคลิกวันที่ ให้ส่งเวลาทั้งหมด (ว่าง/ไม่ว่าง) ของพนักงานคนนั้นกลับไปเป็น JSON
    URL ตัวอย่าง: /employees/7/slots/2025-10-15/
    """
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


def site_massages(request):
    return render(request, 'Massages.html')

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
    return render(request, 'Gallery.html')

def contact(request):
    return render(request, 'contact.html')


def book_online(request):
    """Public booking page: list employees and let visitor pick one to view calendar and book slots."""
    employees = Employee.objects.filter(is_active=True).order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'book_online.html', {'employees': employees})


# ---------------------- UTILITY ----------------------

def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
    return redirect('login')

def _photo_url(emp: Employee):
    data = getattr(emp, 'photo_data', None)
    if data:
        mime = emp.photo_mime or 'image/jpeg'
        b64 = base64.b64encode(data).decode('ascii')
        return f"data:{mime};base64,{b64}"
    return None


# ---------------------- ADMIN DASHBOARD ----------------------

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
def booking_list(request):
    """แสดงรายการคิวจองทั้งหมด พร้อมฟิลเตอร์ตามพนักงานและวันที่"""
    employees = Employee.objects.filter(is_active=True).order_by('display_name')
    selected_emp = request.GET.get('employee')
    selected_date = request.GET.get('date')

    slots = AppointmentSlot.objects.select_related('employee').filter(is_booked=True)

    if selected_emp:
        slots = slots.filter(employee__id=selected_emp)
    if selected_date:
        try:
            day = datetime.strptime(selected_date, "%Y-%m-%d").date()
            slots = slots.filter(date=day)
        except ValueError:
            pass

    slots = slots.order_by('-date', 'start_time')

    context = {
        'slots': slots,
        'employees': employees,
        'selected_emp': selected_emp,
        'selected_date': selected_date,
    }
    return render(request, 'main/booking_list.html', context)


# ---------------------- EMPLOYEE CRUD ----------------------
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


@require_POST
def book_slot(request, slot_id):
    """
    ฟังก์ชันสำหรับจองเวลานัดหมาย (เปลี่ยนสถานะเป็น is_booked=True)
    """
    slot = get_object_or_404(AppointmentSlot, pk=slot_id, is_booked=False)
    slot.is_booked = True
    slot.save(update_fields=['is_booked'])
    return JsonResponse({"success": True, "message": "จองสำเร็จแล้ว!"})

from django.contrib.auth.models import User

def register_view(request):
    """
    หน้าสมัครสมาชิก (Register)
    """
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

# ---------------------- GALLERY CRUD ----------------------

from django.shortcuts import render, redirect, get_object_or_404
from .models import GalleryImage


# ✅ หน้าสำหรับผู้ดูแล (Admin CRUD)
def gallery_list(request):
    """แสดงรายการรูปทั้งหมดในระบบ (สำหรับผู้ดูแล)"""
    gallery = GalleryImage.objects.all().order_by('-created_at')
    return render(request, 'main/gallery_list.html', {'gallery': gallery})


def gallery_add(request):
    """เพิ่มรูปใหม่"""
    if request.method == 'POST':
        title = request.POST.get('title', '')
        image = request.FILES.get('image')
        if image:
            GalleryImage.objects.create(title=title, image=image)
            return redirect('gallery_crud')
    return render(request, 'main/gallery_form.html')


def gallery_edit(request, pk):
    """แก้ไขรูป"""
    image = get_object_or_404(GalleryImage, pk=pk)
    if request.method == 'POST':
        image.title = request.POST.get('title', '')
        if 'image' in request.FILES:
            image.image = request.FILES['image']
        image.save()
        return redirect('gallery_crud')
    return render(request, 'main/gallery_form.html', {'image': image})


def gallery_delete(request, pk):
    """ลบรูป"""
    image = get_object_or_404(GalleryImage, pk=pk)
    image.delete()
    return redirect('gallery_crud')


# ✅ หน้าสำหรับลูกค้าทั่วไป (Public Gallery)
def site_gallery(request):
    """หน้าแสดงภาพแกลเลอรีสำหรับลูกค้า"""
    images = GalleryImage.objects.all().order_by('-created_at')
    return render(request, 'Gallery.html', {'images': images})

# ---------------------- EMPLOYEE AVAILABILITY CRUD ----------------------
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Employee, AppointmentSlot


@login_required
def employee_availability_list(request):
    """หน้าแสดงพนักงานทั้งหมด"""
    employees = Employee.objects.all().order_by('display_name')
    return render(request, 'main/employee_availability_list.html', {'employees': employees})


@login_required
def employee_availability_manage(request, pk):
    """หน้าจัดการเวลาว่างของพนักงานแต่ละคน"""
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
            # แปลงข้อมูลจากฟอร์ม
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()

            # ตรวจสอบว่าเวลาเริ่มต้องน้อยกว่าสิ้นสุด
            if start_time >= end_time:
                messages.error(request, "เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด")
                return redirect('employee_availability_manage', pk=pk)

            # คำนวณระยะเวลา (นาที)
            duration = int((datetime.combine(date, end_time) - datetime.combine(date, start_time)).total_seconds() // 60)

            # ตรวจสอบเวลาทับกัน
            overlap = AppointmentSlot.objects.filter(
                employee=emp,
                date=date,
                start_time=start_time
            ).exists()

            if overlap:
                messages.error(request, "มีช่วงเวลานี้อยู่แล้ว กรุณาเลือกเวลาอื่น")
                return redirect('employee_availability_manage', pk=pk)

            # สร้าง slot ใหม่
            AppointmentSlot.objects.create(
                employee=emp,
                date=date,
                start_time=start_time,
                duration_minutes=duration,
                is_booked=False
            )

            messages.success(request, "เพิ่มเวลาว่างเรียบร้อยแล้ว")
            return redirect('employee_availability_manage', pk=pk)

        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {e}")
            return redirect('employee_availability_manage', pk=pk)

    return render(request, 'main/employee_availability_manage.html', {
        'employee': emp,
        'slots': slots
    })


@login_required
def employee_availability_delete(request, slot_id):
    """ลบเวลาว่างของพนักงาน"""
    slot = get_object_or_404(AppointmentSlot, pk=slot_id)
    emp_id = slot.employee.id
    slot.delete()
    messages.success(request, 'ลบเวลาว่างแล้ว')
    return redirect('employee_availability_manage', pk=emp_id)


@login_required
def availability_select(request):
    """หน้าเลือกพนักงาน (ใช้ถ้ามีหลายสาขา)"""
    employees = Employee.objects.filter(is_active=True).order_by('display_name')
    return render(request, 'main/availability_select.html', {'employees': employees})


# ---------------------- GEMINI (NEW API) ----------------------
from google import genai
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render

from .models import Promotion   # <<< เพิ่มการ import Promotion

client = genai.Client(api_key="AIzaSyBU3lzxF_cemBOF3mh-qcFuoT9R0UUTojM")


def list_models(request):
    try:
        models = client.models.list()
        model_names = [m.name for m in models]
        return JsonResponse({"models": model_names})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def test_gemini(request):
    try:
        response = client.models.generate_content(
            model="models/gemini-2.0-flash-lite",
            contents="สวัสดีจาก Django!"
        )
        return JsonResponse({"reply": response.text})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------------------------------------------
#   โหลดข้อมูลบริการ (Service Info จาก Price.html)
# -------------------------------------------------------------
def load_service_data():
    try:
        with open("main/templates/Price.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "ไม่มีข้อมูลบริการในระบบ"


# -------------------------------------------------------------
#   Chatbot API — เพิ่มระบบโหลดโปรโมชั่นจากฐานข้อมูลแล้ว
# -------------------------------------------------------------
@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=400)

    user_message = request.POST.get("message", "").strip()
    if not user_message:
        return JsonResponse({"error": "ข้อความว่าง"}, status=400)

    # โหลดข้อมูลบริการจากไฟล์
    service_info = load_service_data()

    # ตรวจสอบว่าคำถามเกี่ยวกับโปรโมชั่นหรือไม่
    promo_keywords = ["โปร", "promotion", "โปรโมชั่น", "โปรโมชัน", "ส่วนลด", "offer", "deal"]
    is_promo_question = any(word in user_message.lower() for word in promo_keywords)

    if is_promo_question:
        promos = Promotion.objects.filter(is_active=True).order_by("-updated_at")
        if promos.exists():
            promo_text = "\n".join([f"- {p.title}: {p.description}" for p in promos])
        else:
            promo_text = "ขณะนี้ยังไม่มีโปรโมชั่นพิเศษค่ะ"
        final_prompt = f"""
คุณคือแชตบอทของร้าน Chokdee Thai Massage in Hévíz
ตอบเฉพาะข้อมูลที่ร้านมีจริง ห้ามแต่งเรื่อง

ข้อมูลโปรโมชั่นปัจจุบัน:
{promo_text}

ตอนนี้ลูกค้าถามว่า: \"{user_message}\"

กรุณาตอบด้วยภาษาสุภาพ กระชับ เข้าใจง่าย
ห้ามแต่งข้อมูลเกินจากสิ่งที่ให้ไว้ด้านบน
        """
    else:
        final_prompt = f"""
คุณคือแชตบอทของร้าน Chokdee Thai Massage in Hévíz
ตอบเฉพาะข้อมูลที่ร้านมีจริง ห้ามแต่งเรื่อง

ข้อมูลบริการทั้งหมดมีดังนี้:
{service_info}

ตอนนี้ลูกค้าถามว่า: \"{user_message}\"

กรุณาตอบด้วยภาษาสุภาพ กระชับ เข้าใจง่าย
ห้ามแต่งข้อมูลเกินจากสิ่งที่ให้ไว้ด้านบน
        """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.0-flash-lite",
            contents=final_prompt
        )

        reply_text = response.text
        return JsonResponse({"reply": reply_text}, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------------------------------------------
#   Chat UI
# -------------------------------------------------------------
def chat_ui(request):
    return render(request, "chat.html")



from django.shortcuts import render
from datetime import date
from .models import Booking

def admin_bookings_view(request):
    """ดึงรายการจองจากฐานข้อมูลจริง"""
    bookings = Booking.objects.select_related("employee").order_by("date", "start_time")

    return render(request, "main/admin_bookings.html", {
        "bookings": bookings,
        "today": date.today(),
    })


#---------------------- login/logout views ----------------------

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.conf import settings

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

# ----- Customer Auth (ลูกค้า) -----
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.models import User


def customer_register_view(request):
    # ล้างข้อความค้างก่อนแสดงหน้าใหม่
    storage = messages.get_messages(request)
    for _ in storage:
        pass

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
    # ล้างข้อความค้างก่อนแสดงหน้าใหม่
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_objs = User.objects.filter(email=email)
        found = False
        for user_obj in user_objs:
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"ยินดีต้อนรับ {user_obj.username}!")
                return redirect('home')  # ไปหน้าโฮมของลูกค้า
                found = True
                break
        if not found:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    return render(request, 'main/customer_login.html')


def customer_logout_view(request):
    logout(request)
    messages.success(request, "ออกจากระบบเรียบร้อยแล้ว")
    return redirect('customer_login')

#---------------------- PUBLIC BOOKING SYSTEM ----------------------

def is_conflict(employee, date_obj, start_time, duration):
    """
    ตรวจสอบว่าช่วงเวลานี้ทับกับเวลาที่มีอยู่แล้วหรือไม่
    """
    end_time = (datetime.combine(date_obj, start_time) + timedelta(minutes=duration)).time()

    slots = AppointmentSlot.objects.filter(employee=employee, date=date_obj)

    for s in slots:
        s_end = (datetime.combine(s.date, s.start_time) + timedelta(minutes=s.duration_minutes)).time()

        if start_time < s_end and end_time > s.start_time:
            return True

    return False

# ---------------------- PUBLIC BOOKING SYSTEM ----------------------
from datetime import time

TIME_SLOTS = [
    time(9,0), time(10,0), time(11,0), time(12,0),
    time(13,0), time(14,0), time(15,0), time(16,0),
    time(17,0), time(18,0), time(19,0),
]

def booking_slots(request, employee_id):
    """
    แสดงเวลาทั้งวันของพนักงาน (แบบในภาพ UI ที่คุณส่ง)
    และเช็คว่าเต็มหรือจองได้
    """
    employee = get_object_or_404(Employee, pk=employee_id)

    date_str = request.GET.get("date")
    duration = int(request.GET.get("duration", 60))  # 60 หรือ 120 นาที

    if not date_str:
        return JsonResponse({"error": "missing date"}, status=400)

    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

    slot_list = []
    for slot in TIME_SLOTS:
        conflict = is_conflict(employee, date_obj, slot, duration)
        slot_list.append({
            "time": slot.strftime("%H:%M"),
            "available": not conflict
        })

    return render(request, "main/booking_slots.html", {
        "employee": employee,
        "date": date_str,
        "duration": duration,
        "slots": slot_list,
    })


def booking_form(request):
    """
    หน้าฟอร์มสุดท้ายก่อนบันทึกการจอง
    """
    if request.method == "POST":
        employee_id = request.POST.get("employee")
        date_str = request.POST.get("date")
        duration = int(request.POST.get("duration", 60))
        times = request.POST.getlist("times")

        # รองรับฟอร์มเก่าที่ส่งครั้งเดียว
        single_time = request.POST.get("time")
        if single_time and not times:
            times = [single_time]

        # หากยังไม่มีการเลือกเวลา ให้แจ้งกลับไป
        if not times:
            return render(
                request,
                "main/booking_result.html",
                {"success": False, "message": "กรุณาเลือกเวลาอย่างน้อย 1 ช่วง"}
            )

        # หากยังไม่มีการกรอกชื่อ/เบอร์ ให้แสดงหน้าฟอร์มยืนยันเพื่อกรอก
        customer_name = request.POST.get("customer_name")
        customer_phone = request.POST.get("customer_phone")
        if not customer_name or not customer_phone:
            # หา employee object สำหรับแสดงชื่อสวย ๆ หากทำได้
            employee_obj = None
            if employee_id:
                try:
                    employee_obj = Employee.objects.get(pk=employee_id)
                except Employee.DoesNotExist:
                    employee_obj = None

            return render(request, "main/booking_form.html", {
                "employee": employee_obj.display_name if employee_obj else employee_id,
                "employee_id": employee_id,
                "date": date_str,
                "duration": duration,
                "times": times,
                "error": None,
            })

        # ดำเนินการสร้างการจองเมื่อมีข้อมูลครบ
        try:
            employee = Employee.objects.get(pk=employee_id)
        except Employee.DoesNotExist:
            return render(
                request,
                "main/booking_result.html",
                {"success": False, "message": "ไม่พบพนักงานที่เลือก"}
            )

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return render(
                request,
                "main/booking_result.html",
                {"success": False, "message": "รูปแบบวันที่ไม่ถูกต้อง"}
            )

        created_count = 0
        conflicts = []

        for t in times:
            try:
                start_obj = datetime.strptime(t, "%H:%M").time()
            except ValueError:
                conflicts.append(f"รูปแบบเวลาไม่ถูกต้อง: {t}")
                continue

            if is_conflict(employee, date_obj, start_obj, duration):
                conflicts.append(f"คิวไม่ว่างที่เวลา {t}")
                continue

            Booking.objects.create(
                employee=employee,
                customer_name=customer_name,
                customer_phone=customer_phone,
                date=date_obj,
                start_time=start_obj,
                duration_minutes=duration,
            )
            created_count += 1

        if created_count == 0:
            return render(
                request,
                "main/booking_result.html",
                {"success": False, "message": "ไม่สามารถจองได้ (คิวไม่ว่าง): " + "; ".join(conflicts)}
            )

        msg = f"จองสำเร็จ {created_count} รายการ"
        if conflicts:
            msg += f" (บางช่วงเวลาคิวไม่ว่าง: {'; '.join(conflicts)})"

        return render(
            request,
            "main/booking_result.html",
            {"success": True, "message": msg}
        )

    # GET (แสดงฟอร์ม)
    return render(request, "main/booking_form.html", {
        "employee": request.GET.get("employee"),
        "employee_id": request.GET.get("employee"),
        "date": request.GET.get("date"),
        "time": request.GET.get("time"),
        "times": request.GET.getlist("times"),
        "duration": request.GET.get("duration"),
    })