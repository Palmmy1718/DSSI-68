# ---------------------- 1. IMPORTS (ต้องอยู่บนสุด) ----------------------

import logging
import base64
import os
from urllib.parse import urlencode
from google import genai
from django.conf import settings
from datetime import datetime, timedelta, date, time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bs4 import BeautifulSoup

from .forms import EmployeeForm, PromotionForm
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
        return _("ยังไม่ได้ตั้งค่า GEMINI_API_KEY/GOOGLE_API_KEY ใน .env")
    model_name = (
        getattr(settings, "GEMINI_MODEL_NAME", "")
        or os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    )
    client = genai.Client(api_key=api_key)
    try:
        resp = client.models.generate_content(model=model_name, contents=prompt)
        return getattr(resp, "text", None) or str(resp)
    except Exception as e:
        return f"[Gemini Error] {str(e)}"


# ---------------------- 2. ADMIN VIEWS (MASSAGE - แก้ไขแล้ว) ----------------------

@login_required
def massage_admin_view(request):
    """หน้าหลักจัดการรายการนวด (แสดงรายการ + เพิ่มรายการ)"""
    add_mode = request.GET.get('add') == '1'
    if add_mode and request.method == 'POST':
        # รับค่าภาษาไทย/อังกฤษ (หลัก)
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        # --- รับค่าภาษาเยอรมัน (เพิ่มใหม่) ---
        name_de = request.POST.get('name_de', '').strip()
        description_de = request.POST.get('description_de', '').strip()

        image_file = request.FILES.get('image')

        if not name:
            messages.error(request, _('กรุณากรอกชื่อบริการนวด'))
        else:
            try:
                m = Massage(
                    name=name,
                    description=description or '',
                    # บันทึกภาษาเยอรมัน
                    name_de=name_de,
                    description_de=description_de,
                    price=0,
                    duration=60,
                    image=image_file
                )
                m.save()
                messages.success(request, _('เพิ่มรายการนวดเรียบร้อย'))
                return redirect('massage_admin')
            except Exception as e:
                messages.error(request, _('บันทึกไม่สำเร็จ: %(err)s') % {'err': str(e)})

    massages = Massage.objects.all().order_by('name')
    return render(request, 'main/massage_admin.html', {
        'massages': massages,
        'add_mode': add_mode,
    })


@login_required
def massage_edit(request, pk):
    m = get_object_or_404(Massage, pk=pk)

    if request.method == 'POST':
        # รับค่าภาษาไทย/อังกฤษ (หลัก)
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        # --- รับค่าภาษาเยอรมัน (เพิ่มใหม่) ---
        name_de = request.POST.get('name_de', '').strip()
        description_de = request.POST.get('description_de', '').strip()

        image_file = request.FILES.get('image')

        if not name:
            messages.error(request, _('กรุณากรอกชื่อ'))
        else:
            try:
                m.name = name
                m.description = description
                
                # อัปเดตข้อมูลภาษาเยอรมัน
                m.name_de = name_de
                m.description_de = description_de
                
                if image_file:
                    m.image = image_file

                m.save()
                messages.success(request, _('แก้ไขข้อมูลเรียบร้อย'))
                return redirect('massage_admin')
            except Exception as e:
                messages.error(request, _('บันทึกไม่สำเร็จ: %(err)s') % {'err': str(e)})

    massages = Massage.objects.all().order_by('name')
    return render(request, 'main/massage_admin.html', {
        'massages': massages,
        'edit_mode': True,
        'massage_obj': m
    })


@login_required
def massage_delete(request, pk):
    m = get_object_or_404(Massage, pk=pk)
    m.delete()
    messages.success(request, _('ลบรายการเรียบร้อย'))
    return redirect('massage_admin')


@login_required
def massage_admin_price(request):
    massages = Massage.objects.all().order_by('name')
    if request.method == 'POST':
        updated = 0
        for m in massages:
            changed = False
            # Loop 4 durations
            for dur in [30, 60, 90, 120]:
                field_name = f'price_{dur}'
                input_name = f'price_{dur}_{m.id}'
                
                val_str = request.POST.get(input_name)
                try:
                    val_int = int(val_str) if val_str else 0
                    current_val = getattr(m, field_name)
                    if current_val != val_int:
                        setattr(m, field_name, val_int)
                        changed = True
                except (ValueError, TypeError):
                    continue
            
            if changed:
                m.save()
                updated += 1
                
        if updated:
            messages.success(request, _('อัปเดตราคา %(count)s รายการเรียบร้อย') % {'count': updated})
        else:
            messages.info(request, _('ไม่มีการเปลี่ยนแปลงราคา'))
        return redirect('massage_admin_price')
    return render(request, 'main/massage_admin_price.html', {'massages': massages})


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
        return _("(ไม่สามารถโหลดข้อมูลราคาได้: %(err)s)") % {"err": str(e)}


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


def _safe_next_url(request, fallback='home'):
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse(fallback)


def _customer_login_redirect(next_url):
    return redirect(f"{reverse('customer_login')}?{urlencode({'next': next_url})}")


# ---------------------- 4. FRONTEND PAGES ----------------------

def site_home(request):
    employees = Employee.objects.all().order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'home.html', {'employees': employees})


def site_massages(request):
    from django.utils.translation import get_language
    massages = Massage.objects.all().order_by('name')
    lang = (get_language() or "th").split("-")[0]

    for m in massages:
        if lang == "en":
            m.display_name_i18n = (getattr(m, "name_en", "") or "").strip() or m.name
            m.display_description_i18n = (getattr(m, "description_en", "") or "").strip() or (m.description or "")
        elif lang == "de":
            m.display_name_i18n = (getattr(m, "name_de", "") or "").strip() or m.name
            m.display_description_i18n = (getattr(m, "description_de", "") or "").strip() or (m.description or "")
        else:
            m.display_name_i18n = m.name
            m.display_description_i18n = m.description or ""

    return render(request, "Massages.html", {"massages": massages})


def site_price(request):
    return render(request, 'Price.html')


def site_team(request):
    employees = Employee.objects.all().order_by('display_name')
    for e in employees:
        e.photo_url = _photo_url(e)
    return render(request, 'team.html', {'employees': employees})


def site_promotion(request):
    promotions = Promotion.objects.filter(is_active=True).order_by('-updated_at')
    return render(request, 'Promotion.html', {'promotions': promotions})


def site_gallery(request):
    images = GalleryImage.objects.order_by('-created_at')
    return render(request, 'Gallery.html', {'images': images})


def contact(request):
    return render(request, 'Contact.html')


# ---------------------- 5. CALENDAR & SLOTS API ----------------------

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
            "title": f"{slot.start_time.strftime('%H:%M')}{(' ' + _('(จองแล้ว)')) if slot.is_booked else ''}",
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
        return JsonResponse({"error": _("รูปแบบวันที่ไม่ถูกต้อง")}, status=400)

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


# ---------------------- 6. ADMIN DASHBOARD & EMPLOYEE CRUD ----------------------

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
            messages.success(request, _('เพิ่มพนักงานแล้ว'))
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'main/employee_form.html', {'form': form, 'title': _('เพิ่มพนักงาน'), 'photo_url': None})


# ---------------------- 7. GALLERY CRUD ----------------------

@login_required
def gallery_list(request):
    gallery = GalleryImage.objects.order_by('-created_at')
    return render(request, 'main/gallery_list.html', {'gallery': gallery})


@login_required
def gallery_add(request):
    if request.method == 'POST':
        image_file = request.FILES.get('image')
        if not image_file:
            messages.error(request, _('กรุณาอัปโหลดรูปภาพ'))
        else:
            try:
                g = GalleryImage(image=image_file)
                g.save()
                messages.success(request, _('เพิ่มรูปภาพสำเร็จ'))
                return redirect('gallery_crud')
            except Exception as e:
                messages.error(request, _('บันทึกล้มเหลว: %(err)s') % {'err': str(e)})
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
            messages.success(request, _('แก้ไขรูปภาพสำเร็จ'))
            return redirect('gallery_crud')
        except Exception as e:
            messages.error(request, _('บันทึกล้มเหลว: %(err)s') % {'err': str(e)})
    return render(request, 'main/gallery_form.html', {'item': g})


@login_required
@require_POST
def gallery_delete(request, pk):
    g = get_object_or_404(GalleryImage, pk=pk)
    g.delete()
    messages.success(request, _('ลบรูปภาพแล้ว'))
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
            messages.success(request, _('อัปเดตข้อมูลแล้ว'))
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=emp)
    return render(request, 'main/employee_form.html', {
        'form': form,
        'title': _('แก้ไข: %(name)s') % {'name': emp.display_name},
        'photo_url': _photo_url(emp)
    })


@staff_required
def employee_delete_view(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        emp.delete()
        messages.success(request, _('ลบพนักงานแล้ว'))
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
        messages.success(request, _('อัปเดตชื่อแล้ว'))
    else:
        messages.error(request, _('ชื่อห้ามว่าง'))
    return redirect('employee_list')


@staff_required
@require_POST
def employee_quick_photo(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    f = request.FILES.get('photo_file')
    if not f:
        messages.error(request, _('กรุณาเลือกไฟล์รูป'))
        return redirect('employee_list')
    emp.photo_mime = getattr(f, 'content_type', 'image/jpeg') or 'image/jpeg'
    emp.photo_data = f.read()
    emp.save(update_fields=['photo_mime', 'photo_data'])
    messages.success(request, _('เปลี่ยนรูปแล้ว'))
    return redirect('employee_list')


@staff_required
@require_POST
def employee_clear_photo(request, pk):
    emp = get_object_or_404(Employee, pk=pk)
    emp.photo_data = None
    emp.photo_mime = None
    emp.save(update_fields=['photo_data', 'photo_mime'])
    messages.success(request, _('ลบรูปแล้ว'))
    return redirect('employee_list')


# ---------------------- 8. GALLERY CRUD ----------------------

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
                messages.success(request, _('เพิ่มเวลาว่างเรียบร้อย'))
            except Exception:
                messages.error(request, _('ข้อมูลวันที่/เวลาไม่ถูกต้อง'))
            return redirect('employee_availability', pk=pk)

        elif action == 'delete':
            slot_id = request.POST.get('slot_id')
            AppointmentSlot.objects.filter(pk=slot_id, employee=emp).delete()
            messages.success(request, _('ลบเวลาว่างแล้ว'))
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
            messages.error(request, _("กรุณากรอกข้อมูลให้ครบถ้วน"))
            return redirect('employee_availability_manage', pk=pk)

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_str, '%H:%M').time()
            end_time_obj = datetime.strptime(end_str, '%H:%M').time()

            if start_time_obj >= end_time_obj:
                messages.error(request, _("เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุด"))
                return redirect('employee_availability_manage', pk=pk)

            duration = int((datetime.combine(date_obj, end_time_obj) - datetime.combine(date_obj, start_time_obj)).total_seconds() // 60)
            overlap = AppointmentSlot.objects.filter(employee=emp, date=date_obj, start_time=start_time_obj).exists()
            if overlap:
                messages.error(request, _("มีช่วงเวลานี้อยู่แล้ว กรุณาเลือกเวลาอื่น"))
                return redirect('employee_availability_manage', pk=pk)

            AppointmentSlot.objects.create(
                employee=emp, date=date_obj, start_time=start_time_obj,
                duration_minutes=duration, is_booked=False
            )
            messages.success(request, _("เพิ่มเวลาว่างเรียบร้อยแล้ว"))
            return redirect('employee_availability_manage', pk=pk)

        except Exception as e:
            messages.error(request, _("เกิดข้อผิดพลาด: %(err)s") % {"err": str(e)})
            return redirect('employee_availability_manage', pk=pk)

    return render(request, 'main/employee_availability_manage.html', {'employee': emp, 'slots': slots})


@login_required
def employee_availability_delete(request, slot_id):
    slot = get_object_or_404(AppointmentSlot, pk=slot_id)
    emp_id = slot.employee.id
    slot.delete()
    messages.success(request, _('ลบเวลาว่างแล้ว'))
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
    bookings = Booking.objects.filter(employee=employee, date=date_obj).exclude(status="cancelled")
    for b in bookings:
        b_start = b.start_time
        b_end = (datetime.combine(date_obj, b_start) + timedelta(minutes=b.duration_minutes or 60)).time()
        if start_time < b_end and end_time > b_start:
            return True
    slots = AppointmentSlot.objects.filter(employee=employee, date=date_obj)
    for s in slots:
        s_end = (datetime.combine(s.date, s.start_time) + timedelta(minutes=s.duration_minutes)).time()
        if start_time < s_end and end_time > s.start_time:
            return True
    return False


def booking_slots(request, employee_id):
    if not request.user.is_authenticated:
        messages.info(request, _("กรุณาเข้าสู่ระบบก่อนจองคิว หากยังไม่มีบัญชี โปรดสมัครสมาชิกก่อน"))
        return _customer_login_redirect(request.get_full_path())

    employee = get_object_or_404(Employee, pk=employee_id)
    date_str = request.GET.get("date")
    duration = int(request.GET.get("duration", 60))

    if not date_str:
        date_str = date.today().strftime("%Y-%m-%d")

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": _("รูปแบบวันที่ไม่ถูกต้อง")}, status=400)

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
    if not request.user.is_authenticated:
        employee_id = request.POST.get("employee")
        date_str = request.POST.get("date")
        duration = request.POST.get("duration", 60)

        next_url = reverse('home')
        if employee_id and date_str:
            next_url = f"{reverse('booking_slots', args=[employee_id])}?{urlencode({'date': date_str, 'duration': duration})}"

        messages.info(request, _("กรุณาเข้าสู่ระบบก่อนจองคิว หากยังไม่มีบัญชี โปรดสมัครสมาชิกก่อน"))
        return _customer_login_redirect(next_url)

    if request.method == "POST":
        employee_id = request.POST.get("employee")
        date_str = request.POST.get("date")
        duration = int(request.POST.get("duration", 60))
        times = request.POST.getlist("times")
        single_time = request.POST.get("time")

        if single_time and not times:
            times = [single_time]

        if not times:
            return render(request, "main/booking_result.html", {
                "success": False,
                "message": _("กรุณาเลือกเวลาอย่างน้อย 1 ช่วง")
            })

        customer_name = request.POST.get("customer_name") or request.user.get_full_name() or request.user.username
        customer_phone = request.POST.get("customer_phone")

        employee_obj = None
        if employee_id:
            try:
                employee_obj = Employee.objects.get(pk=employee_id)
            except Employee.DoesNotExist:
                pass

        if not customer_name or not customer_phone:
            return render(request, "main/booking_form.html", {
                "employee": employee_obj.display_name if employee_obj else employee_id,
                "employee_id": employee_id,
                "date": date_str,
                "duration": duration,
                "times": times,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "error": None,
            })

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return render(request, "main/booking_result.html", {"success": False, "message": _("รูปแบบวันที่ไม่ถูกต้อง")})

        if not employee_obj:
            return render(request, "main/booking_result.html", {"success": False, "message": _("ไม่พบพนักงานที่เลือก")})

        created_count = 0
        conflicts = []
        from django.db import IntegrityError

        for t in times:
            try:
                start_obj = datetime.strptime(t, "%H:%M").time()
            except ValueError:
                conflicts.append(_("รูปแบบเวลาไม่ถูกต้อง: %(t)s") % {"t": t})
                continue

            if is_conflict(employee_obj, date_obj, start_obj, duration):
                conflicts.append(_("คิวยังไม่ว่างที่เวลา %(t)s") % {"t": t})
                continue

            try:
                Booking.objects.create(
                    employee=employee_obj,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    date=date_obj,
                    start_time=start_obj,
                    duration_minutes=duration,
                )
                created_count += 1
            except IntegrityError:
                conflicts.append(_("คิวยังไม่ว่างที่เวลา %(t)s") % {"t": t})

        if created_count == 0:
            return render(request, "main/booking_result.html", {
                "success": False,
                "message": _("ไม่สามารถจองได้: %(detail)s") % {"detail": "; ".join(conflicts)}
            })

        msg = _("จองสำเร็จ %(count)s รายการ") % {"count": created_count}
        if conflicts:
            msg += _(" (บางรายการไม่ได้: %(detail)s)") % {"detail": "; ".join(conflicts)}

        return render(request, "main/booking_result.html", {"success": True, "message": msg})

    return redirect('home')


@require_POST
def book_slot(request, slot_id):
    slot = get_object_or_404(AppointmentSlot, pk=slot_id, is_booked=False)
    slot.is_booked = True
    slot.save(update_fields=['is_booked'])
    return JsonResponse({"success": True, "message": _("จองสำเร็จแล้ว!")})


# ---------------------- 10. BOOKING LIST (ADMIN) ----------------------

@login_required
def booking_list(request):
    return admin_bookings_view(request)


@login_required
def admin_bookings_view(request):
    qs = Booking.objects.select_related("employee").order_by("-date", "-start_time", "-id")
    q_date = request.GET.get("date")
    if q_date:
        try:
            qd = datetime.strptime(q_date, "%Y-%m-%d").date()
            qs = qs.filter(date=qd).order_by("-date", "-start_time", "-id")
        except Exception:
            pass

    bookings = list(qs)
    date_to_idx = {}
    idx = 0

    for b in bookings:
        try:
            start = b.start_time
            duration = getattr(b, 'duration_minutes', 60) or 60
            dt_start = datetime.combine(b.date, start)
            dt_end = dt_start + timedelta(minutes=duration)
            b.time_range = f"{start.strftime('%H:%M')}-{dt_end.strftime('%H:%M')}"
        except Exception:
            b.time_range = ""

        d = b.date
        if d not in date_to_idx:
            date_to_idx[d] = idx
            idx += 1
        b.day_idx = date_to_idx[d] % 5

    return render(request, "main/admin_bookings.html", {
        "bookings": bookings,
        "today": date.today(),
        "q_date": q_date or "",
    })


@login_required
@require_POST
def admin_booking_confirm(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.status = "confirmed"
    b.save()
    messages.success(request, _("ยืนยันการจองเรียบร้อย"))
    return redirect(request.POST.get("return") or "admin_bookings")


@login_required
@require_POST
def admin_booking_cancel(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.status = "cancelled"
    b.save()
    messages.success(request, _("ยกเลิกการจองเรียบร้อย"))
    return redirect(request.POST.get("return") or "admin_bookings")


@login_required
@require_POST
def admin_booking_delete(request, pk):
    b = get_object_or_404(Booking, pk=pk)
    b.delete()
    messages.success(request, _("ลบการจองแล้ว"))
    return redirect(request.POST.get("return") or "admin_bookings")


# ---------------------- 11. AUTHENTICATION ----------------------

def register_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        if password != confirm:
            messages.error(request, _("รหัสผ่านไม่ตรงกัน"))
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, _("ชื่อผู้ใช้นี้มีอยู่แล้ว"))
            return redirect('register')
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, _("สมัครสมาชิกสำเร็จ! โปรดเข้าสู่ระบบ"))
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
            messages.error(request, _("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"))
    return render(request, "main/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, _("ออกจากระบบเรียบร้อยแล้ว"))
    return redirect("login")


def customer_register_view(request):
    next_url = _safe_next_url(request)

    if request.user.is_authenticated:
        return redirect(next_url)

    storage = messages.get_messages(request)
    for _message in storage:
        pass

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        if password != confirm:
            messages.error(request, _("รหัสผ่านไม่ตรงกัน"))
            return redirect(f"{reverse('customer_register')}?{urlencode({'next': next_url})}")
        if User.objects.filter(username=username).exists():
            messages.error(request, _("ชื่อผู้ใช้นี้มีอยู่แล้ว"))
            return redirect(f"{reverse('customer_register')}?{urlencode({'next': next_url})}")
        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, _("สมัครสมาชิกสำเร็จ! โปรดเข้าสู่ระบบ"))
        return redirect(f"{reverse('customer_login')}?{urlencode({'next': next_url})}")
    return render(request, 'main/customer_register.html', {'next_url': next_url})


def customer_login_view(request):
    next_url = _safe_next_url(request)

    if request.user.is_authenticated:
        return redirect(next_url)

    storage = messages.get_messages(request)
    for _message in storage:
        pass

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        UserModel = get_user_model()
        user_objs = UserModel.objects.filter(email=email)

        for user_obj in user_objs:
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(
                    request,
                    _("ยินดีต้อนรับ %(name)s!") % {"name": user_obj.username}
                )
                return redirect(next_url)

        messages.error(request, _("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"))

    return render(request, 'main/customer_login.html', {'next_url': next_url})


def customer_logout_view(request):
    logout(request)
    messages.success(request, _("ออกจากระบบเรียบร้อยแล้ว"))
    return redirect('customer_login')


# ---------------------- 12. PROMOTION MANAGEMENT (ADMIN) ----------------------

@login_required
def admin_promotion_list(request):
    promotions = Promotion.objects.all().order_by('-updated_at')
    return render(request, 'main/admin_promotion_list.html', {'promotions': promotions})


@login_required
def admin_promotion_add(request):
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_promotion_list')
    else:
        form = PromotionForm()
    return render(request, 'main/admin_promotion_form.html', {'form': form, 'add_mode': True})


@login_required
def admin_promotion_edit(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promo)
        if form.is_valid():
            form.save()
            return redirect('admin_promotion_list')
    else:
        form = PromotionForm(instance=promo)
    return render(request, 'main/admin_promotion_form.html', {'form': form, 'edit_mode': True})


@login_required
@require_POST
def admin_promotion_toggle(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    promo.is_active = not promo.is_active
    promo.save()
    status_msg = _("เปิดใช้งาน") if promo.is_active else _("ปิดใช้งาน")
    messages.success(request, _('เปลี่ยนสถานะเป็น %(status)s แล้ว') % {'status': status_msg})
    return redirect('admin_promotion_list')


@login_required
@require_POST
def admin_promotion_delete(request, pk):
    promo = get_object_or_404(Promotion, pk=pk)
    promo.delete()
    messages.success(request, _('ลบโปรโมชั่นเรียบร้อย'))
    return redirect('admin_promotion_list')
# ---------------------- 13. CHAT (Dummy) ----------------------

@login_required # Optional, considering if chat is public or not. User said simple dummy. Usually chat UI might be public. Let's stick to simple.
def chat_ui(request):
    return render(request, 'chat.html')

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        return JsonResponse({'response': 'This is a dummy response.'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

