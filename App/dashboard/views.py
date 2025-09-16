from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import stripe
import zipfile
from django.views import View
import pandas as pd
from django.http import HttpResponse
import os
from django.contrib import messages
from django.urls import reverse
from django.views.generic import TemplateView
from .models import Product
from qrcodes.models import Event, EventRole, QRCode, Ticket, Payment, TicketAssignment, EventInvite
from qrcodes.tasks import send_event_qr_codes
import tempfile
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from PIL import Image
import io
from django.db.models import Count, Q, Sum
from io import BytesIO
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile
from .forms import UserEmailForm, ShareQRCodeForm, EventUpdateForm,UpdateQRCodesForm, TicketAssignmentForm, AutoTicketAssignmentForm
from .forms import MyPostForm, EventSelectorForm, InviteForm  # Este es tu formulario definido
from .forms import PrintQRForm
from .forms import EventRecycleForm
from django.contrib.auth import logout
from fpdf import FPDF
from qrcodes.utils.event_mask import save_event_mask
from qrcodes.utils.qr_render_db import compose_qr_from_db
from qrcodes.utils.footer_presets import get_footer_preset
from .ads_selector import get_banner_for_country
from django.utils.timezone import localtime
from .ads_selector import get_banner_for_country  # tu selector
from django.utils import timezone

def force_logout_view(request):
    logout(request)
    return redirect('login')  # Redirige a tu vista de login o donde quieras
################################################
#   Metodo de archivo temporal
################################################
def create_temp_file(uploaded_file):
    """Creates a temporary file with the correct image format."""
    
    # Open the image to detect its format
    image = Image.open(uploaded_file)
    image_format = image.format.lower()  # Example: "jpeg", "png", "webp"

    # Standardize JPEG extension
    if image_format == "jpeg":
        image_format = "jpg"

    # Create a temporary file with the detected format
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{image_format}")

    # Save image to the temporary file
    buffer = io.BytesIO()
    image.save(buffer, format=image.format)
    buffer.seek(0) 

    # Write buffer contents to temp file
    temp_file.write(buffer.getvalue())
    
    temp_file.flush()  # Ensure data is written to disk

    print(f"✅ Temporary file created: {temp_file.name}")

    return temp_file
################################################
#   Compartir pdf
################################################

@login_required
def download_available_qr_pdf(request, event_id):
    event = get_object_or_404(Event, id=event_id, created_by=request.user)
    available_qs = event.qr_codes.filter(status_purchased='available')
    available_count = available_qs.count()

    if available_count == 0:
        return HttpResponse("No available QR codes to export.", status=404)

    # —— If this is a GET with ?quantity=… we stream the PDF —— 
    if request.method == 'GET' and 'quantity' in request.GET:
        qty = int(request.GET['quantity'])
        # clamp to available
        qty = min(qty, available_count)
        to_print = list(available_qs[:qty])

        pdf = FPDF(unit='cm', format=(8, 8))
        for qr in to_print:
            pdf.add_page()
            pdf.image(qr.image.path, x=0, y=0, w=8, h=8)

        # mark them purchased
        QRCode.objects.filter(id__in=[qr.id for qr in to_print]) \
                        .update(status_purchased='purchased')

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"qr_print_{event.name}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # —— Otherwise POST or initial GET: show form only —— 
    if request.method == 'POST':
        # we don’t actually need to do anything here,
        # JS will trigger the GET-download+redirect
        form = PrintQRForm(available_count, request.POST)
    else:
        form = PrintQRForm(available_count, initial={'quantity': available_count})

    return render(request, 'dashboard/print_qr_form.html', {
        'event': event,
        'form': form,
        'available_count': available_count,
    })
################################################
#   Compartir QR
################################################
def share_qr_codes(request, event_id):
    # 🔒 only owner can share
    event = get_object_or_404(Event, id=event_id, created_by=request.user)

    if request.method == 'POST':
        form = ShareQRCodeForm(request.POST)
        if form.is_valid():
            recipient_email = form.cleaned_data['recipient_email']
            number_of_codes = form.cleaned_data['number_of_codes']

            # grab only “available” codes
            available = event.qr_codes.filter(status_purchased='available')[:number_of_codes]
            if available.count() < number_of_codes:
                form.add_error('number_of_codes',
                    f'Only {available.count()} QR codes are available.'
                )
            else:
                # build the ZIP in memory
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    codes_shared = []
                    for qr in available:
                        qr.status_purchased = 'purchased'
                        qr.user_email = recipient_email
                        qr.save()

                        # write the image file into the zip
                        path = os.path.join(settings.MEDIA_ROOT,
                                            'qrcodes',
                                            f"qr_{qr.id}_.png")
                        if os.path.exists(path):
                            zf.write(path, os.path.basename(path))
                        codes_shared.append(qr.data)

                zip_buffer.seek(0)

                # send email
                subject = f"QR Codes for Event: {event.name}"
                message = (
                    f"You have been granted access to the event: {event.name}\n\n"
                    f"Attached are your {number_of_codes} QR codes."
                )
                email = EmailMessage(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient_email]
                )
                email.attach(f"{event.name}_QR_Codes.zip",
                             zip_buffer.getvalue(),
                             "application/zip")
                email.send()

                return render(request, 'dashboard/share_confirmation.html', {
                    'event':          event,
                    'recipient_email': recipient_email,
                    'codes_shared':    codes_shared,
                    'remaining_codes': event.qr_codes.filter(
                                           status_purchased='available'
                                       ).count()
                })
    else:
        form = ShareQRCodeForm()

    return render(request, 'dashboard/shareqr.html', {
        'event': event,
        'form':  form
    })
################################################
#   Pagina de bienvenida report
################################################
def export_qr_summary_to_excel(request):
    user = request.user  # Usuario autenticado

    # Obtener el total de QR comprados por el usuario en todos sus eventos
    total_qr_purchased_by_user = QRCode.objects.filter(
        event__created_by=user,
        status_purchased='purchased'
    ).count()

    # Obtener los datos de cada evento
    events = Event.objects.filter(created_by=user).annotate(
        total_qr_count=Count('qr_codes'),
        purchased_qr_count=Count('qr_codes', filter=Q(qr_codes__status_purchased='purchased'))
    ).values("name", "total_qr_count", "purchased_qr_count")

    # Convertir los datos a un DataFrame de pandas
    df = pd.DataFrame(list(events))

    # Agregar una fila con el total de QR comprados por el usuario
    df.loc[len(df)] = ["# QR sold by the user", "", total_qr_purchased_by_user]

    # Crear la respuesta HTTP con el archivo Excel
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="qr_summary.xlsx"'

    # Guardar el archivo en la respuesta HTTP
    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resumen de QR")

    return response

################################################
#   export qr codes
################################################

@login_required
def export_qr_codes_to_excel(request, event_id):
    user = request.user
    # Buscar evento por ID y asegurar que pertenece al usuario
    event = get_object_or_404(Event, id=event_id, created_by=user)
    qr_codes = event.qr_codes.all()

    if not qr_codes.exists():
        return HttpResponse("No hay códigos QR disponibles para este evento.", status=404)

    # Estructurar los datos
    data = [
        {
            "id": qr.id,
            "code": qr.data,
            "Status": qr.status_purchased,
        }
        for qr in qr_codes
    ]

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"qr_codes_{event.name}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="QR Codes")

    return response


################################################
#   Pagina de bienvenida
################################################
@login_required
def inicio(request):
    template = 'dashboard/index.html' 
    user_name = request.user
    user_id = request.user.id
    user_events = Event.objects.filter(created_by=user_id)
    qr_codes_list = [qr for event in user_events for qr in event.qr_codes.all()]
    # available_qrs = user_events.qr_codes.filter(status_purchased="available")
    print(len(qr_codes_list))
    paid_tickets_total = Ticket.objects.filter(
        user_name=user_id,
        is_paid=True
        ).aggregate(total=Sum('quantity'))['total'] or 0
    
    total_qr_purchased_by_user = QRCode.objects.filter(
        event__created_by=user_id,
        status_purchased='purchased'
    ).count()
    total_qr_recycled_by_user = QRCode.objects.filter(
        event__created_by=user_id,
        status_recycled='recycled'
    ).count()
    tickets = Ticket.objects.filter(user_name=user_id, is_paid=True)
    total_unassigned = sum(t.unassigned_quantity() for t in tickets)
    available_codes_count = total_unassigned 
    total_tickets_purchased= tickets.count()
    total_qr_used_by_user = QRCode.objects.filter(
        event__created_by=user_id,
        status_scan='concedido'
    ).count()
    total_qr_available_by_user = QRCode.objects.filter(
        event__created_by=user_id,
        status_purchased='available'
    ).count()
# sql nombre del evento, # qr, # ventas, generar un reporte en excel
    events_with_purchased_qr_count = Event.objects.filter(created_by=user_id).annotate(
        total_qr_count=Count('qr_codes'),  # Total de QR asociados al evento
        purchased_qr_count=Count('qr_codes', filter=Q(qr_codes__status_purchased='purchased'))
    )    
    print(events_with_purchased_qr_count)
    for event in events_with_purchased_qr_count:
        print(f"Evento: {event.name}, QR Comprados: {event.purchased_qr_count}")
        print(event.total_qr_count)
    form = MyPostForm(request.POST)

    if request.method == "POST":
        if request.POST['solicitud'] =='paid':
            print(request.POST['solicitud'])
            ticket_db = Ticket.objects.create(
                user_name = user_name,
                quantity = request.POST["quantity"],
                is_paid = False
            )
            quantity = request.POST["quantity"]
            messages.success(
                request,
                f"✅ Ticket created for {quantity} QRs."
            )
            url = reverse('dashboard:create_checkout_session', kwargs={'pk': ticket_db.id })
            return redirect(url)
        if request.POST['solicitud'] == 'free':
            print(request.POST['solicitud'])
            ticket_db = Ticket.objects.create(
                user_name = user_name,
                quantity = request.POST["quantity"],
                is_paid = False,
                plan = 'free',
                ads_enabled = True
            )
            quantity = request.POST["quantity"]
            messages.success(
            request,
            f"🎉  Ticket created FREE with Ads: {quantity} QR(s) enabled."
            )
            url= reverse('dashboard:inicio')
            return redirect(url)
    print(user_events)
    context = {'user':user_name, "NC":str(len(qr_codes_list)), "NE":str(len(user_events)), "purchased":total_qr_purchased_by_user+available_codes_count, 'tp':total_qr_used_by_user,
               'available':available_codes_count,'used':total_qr_purchased_by_user, 'recycle':total_qr_recycled_by_user,
               'form': form}
    return render(request, template, context)
################################################
#   Pagina de QR Generador
################################################
def qrgen(request):
    template = 'dashboard/qrgenerator.html' 
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR Escaner
################################################
def qrscan(request):
    user = request.user
    # Si el usuario tiene eventos como monitor, le pasamos solo esos
    monitored = user.monitored_events.all()
    if monitored.exists():
        form = EventSelectorForm(events=monitored)
    else:
        # Comprador: seguimos con la lógica original
        form = EventSelectorForm(user=user)

    websocket_url = 'wss://app.manillasbolivia.com/ws/qr/'
    return render(request, 'dashboard/qrscan.html', {
        'websocket_url': websocket_url,
        'user': user,
        'form': form
    }) 
################################################
#   Pagina compartir evento
################################################
@login_required
def invite_user(request, event_id):
    event = get_object_or_404(Event, id=event_id, created_by=request.user)

    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            invite, created = EventInvite.objects.get_or_create(event=event, email=email)
            registration_link = request.build_absolute_uri(
                reverse("signup") + f"?email={invite.email}"
            )

            # Enviar correo al invitado
            send_mail(
                subject=f"Te invitaron al evento: {event.name}",
                message=(
                    f"Hola,\n\nHas sido invitado al evento '{event.name}'. "
                    f"Para registrarte y acceder, haz clic aquí: {registration_link}\n\n"
                    "Gracias."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invite.email],
            )

            return render(request, "dashboard/success_invite.html", {"event": event, "email": email})
    else:
        form = InviteForm()

    return render(request, "dashboard/invite.html", {"form": form, "event": event})
################################################
# QR SCAN para invitados
################################################
@login_required
def qrscan_invited(request):
    accepted = EventInvite.objects.filter(
        email=request.user.email,
        accepted=True
    ).select_related('event')
    if not accepted:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    invited_events = [inv.event for inv in accepted]
    form = EventSelectorForm(user=request.user, events=invited_events)
    return render(request, 'dashboard/qrscan_invited.html', {
        'form': form, 'user': request.user
    })

################################################
#   Pagina de QR create event
################################################
def create(request):
    template = 'dashboard/create.html' 
    user_name = request.user
    product1 = Product.objects.get(name="Plan 1")
    product2 = Product.objects.get(name="Plan 2")
    product3 = Product.objects.get(name="Plan 3")
    print(product1.id)
    
    context = {
        "product1": product1,
        "product2": product2,
        "product3": product3, 
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        'user':user_name
        }
    return render(request, template, context)
################################################
#   Pagina de QR create tickets
################################################
class ShowModalView(View):
    def get(self, request):
        form = MyPostForm()
        return render(request, 'create_ticket.html', {'form': form})

class ProcessFormView(View):
    def post(self, request):
        form = MyPostForm(request.POST)
        if form.is_valid():
            # Aquí podrías guardar los datos o iniciar una sesión de pago
            # por ejemplo: payment = create_stripe_session(...)
            return redirect('dashboard:inicio')  # o cualquier otra vista
        return render(request, 'create_ticket.html', {'form': form})

def recycle_available_qrs(event):
    qrs_to_recycle = event.qr_codes.filter(
        status_purchased="available",  # no fueron comprados
        status_recycled="available"   # aún no están marcados como reciclados
    )
    count = qrs_to_recycle.count()
    qrs_to_recycle.update(status_recycled="recycled")
    return count

def count_available_to_recycle(event):
    return event.qr_codes.filter(
        status_purchased="available",
        status_recycled="available"
    ).count()

def reciclar_qr_evento(request, id):
    event = get_object_or_404(Event, id=id, created_by=request.user)

    # 1️⃣ Solo contamos, no reciclamos
    recyclable_count = count_available_to_recycle(event)

    if request.method == "POST":
        form = EventRecycleForm(request.POST, user=request.user, event_id=id)
        if form.is_valid():
            confirm = form.cleaned_data['recycle_confirm']
            if confirm == 'yes':
                # 2️⃣ Reciclamos aquí, y **solo** si confirmó sí
                recycled_count = recycle_available_qrs(event)
                messages.success(
                    request,
                    f"♻️ Se reciclaron {recycled_count} QR disponibles del evento '{event.name}'."
                )
            else:
                messages.info(
                    request,
                    f"❌ Reciclaje cancelado para el evento '{event.name}'."
                )
            return redirect('dashboard:tables')
    else:
        form = EventRecycleForm(user=request.user, event_id=id)

    return render(request, "dashboard/reciclar_qr_evento.html", {
        "form": form,
        "event": event,
        "recyclable_count": recyclable_count,  # opcional, para mostrar “hay X a reciclar”
    })

################################################
#   Pagina de QR view events form db
################################################
# @login_required
# def listdb(request):
#     template = 'dashboard/tables_event.html'
#     user_name = request.user
#     user_id = request.user.id
#     if request.method == "POST":
#         form = AutoTicketAssignmentForm(request.POST, user=request.user)
#         event_name = request.POST['event']
#         quantity_to_assign = int(request.POST['quantity'])
#         # 1️⃣ Verificar si hay suficientes tickets disponibles
#         tickets = Ticket.objects.filter(user_name=user_id, is_paid=True)
#         total_unassigned = sum(t.unassigned_quantity() for t in tickets)
#         print("Total>",total_unassigned)
#         print("Asignado",quantity_to_assign)
#         if total_unassigned < quantity_to_assign:
#             messages.error(request, f"Tienes solo {total_unassigned} tickets no asignados. No se puede crear el evento.")
#             # user_events = Event.objects.filter(created_by=user_id)
#             user_events = Event.objects.filter(created_by=user_id).annotate(
#                 recycled_count=Count(
#                     'qr_codes',
#                     filter=Q(qr_codes__status_recycled='recycled')
#                 )
#              )
#             print(user_events)
#             context = {'events': user_events, 'user':user_name,'form':form}
#             return render(request, template, context)

#         # 2️⃣ Crear imagen temporal en blanco
#         image_save = Image.new('RGB', (300, 300), color='white')
#         buffer = io.BytesIO()
#         image_save.save(buffer, format="jpeg")
#         buffer.seek(0)
#         temp_image_file = InMemoryUploadedFile(
#             buffer, None, "temp_image.png", "image/png", sys.getsizeof(buffer), None
#         )

#         # 3️⃣ Crear evento
#         event = Event.objects.create(
#             name=event_name,
#             created_by=user_name,
#             qr_code_count=quantity_to_assign,
#             image=temp_image_file
#         )

#         # 4️⃣ Asignar a tickets disponibles
#         remaining = quantity_to_assign
#         for ticket in tickets:
#             unassigned = ticket.unassigned_quantity()
#             if unassigned > 0:
#                 assign_now = min(remaining, unassigned)
#                 TicketAssignment.objects.create(
#                     ticket=ticket,
#                     event=event.name,
#                     quantity=assign_now,
#                     event_fk=event
#                 )
#                 remaining -= assign_now
#             if remaining == 0:
#                 break

#         # 5️⃣ Enviar códigos QR
#         send_event_qr_codes.delay(event.id)

#         messages.success(request, f"Se asignaron {quantity_to_assign} códigos QR al evento '{event.name}' correctamente.")
#         return redirect('dashboard:inicio')
#     else:
#         form = AutoTicketAssignmentForm(user=user_id)
#         # user_events = Event.objects.filter(created_by=user_id)
#         user_events = Event.objects.filter(created_by=user_id).annotate(
#             recycled_count=Count(
#                 'qr_codes',
#                 filter=Q(qr_codes__status_recycled='recycled')
#             )
#     )
#         context = {'events': user_events, 'user':user_name,'form':form}
#         return render(request, template, context)

@login_required
def listdb(request):
    template = 'dashboard/tables_event.html'
    user_name = request.user
    user_id = request.user.id

    if request.method == "POST":
        form = AutoTicketAssignmentForm(request.POST, request.FILES, user=request.user)
        # if not form.is_valid():
        #     messages.error(request, "Formulario inválido.")
        #     user_events = Event.objects.filter(created_by=user_id).annotate(
        #         recycled_count=Count('qr_codes', filter=Q(qr_codes__status_recycled='recycled'))
        #     )
        #     return render(request, template, {'events': user_events, 'user': user_name, 'form': form})

        # event_name = form.cleaned_data['event']
        # quantity_to_assign = int(form.cleaned_data['quantity'])
        # free_with_ads = form.cleaned_data.get('free_with_ads') is True

        event_name = form['event']
        quantity_to_assign = int(request.POST['id_quantity'])
        free_with_ads = form['free_with_ads'] is True

        # 1) verificar tickets
        tickets = Ticket.objects.filter(user_name=user_id, is_paid=True)
        total_unassigned = sum(t.unassigned_quantity() for t in tickets)

        if total_unassigned < quantity_to_assign and not free_with_ads:
            messages.error(request,
                f"Tienes solo {total_unassigned} tickets no asignados. "
                f"Marca 'Crear gratis con publicidad' para continuar.")
            user_events = Event.objects.filter(created_by=user_id).annotate(
                recycled_count=Count('qr_codes', filter=Q(qr_codes__status_recycled='recycled'))
            )
            return render(request, template, {'events': user_events, 'user': user_name, 'form': form})

        # 2) imagen temporal (respetar pipeline actual)
        image_save = Image.new('RGB', (300, 300), color='white')
        buffer = io.BytesIO()
        image_save.save(buffer, format="jpeg")
        buffer.seek(0)
        temp_image_file = InMemoryUploadedFile(
            buffer, None, "temp_image.png", "image/png", sys.getsizeof(buffer), None
        )

        # 3) crear evento
        event = Event.objects.create(
            name=event_name,
            created_by=user_name,
            qr_code_count=quantity_to_assign,
            image=temp_image_file
        )

        # 4) si NO es free → asignar a tickets
        if not free_with_ads:
            remaining = quantity_to_assign
            for ticket in tickets:
                unassigned = ticket.unassigned_quantity()
                if unassigned > 0:
                    assign_now = min(remaining, unassigned)
                    TicketAssignment.objects.create(
                        ticket=ticket,
                        event=event.name,
                        quantity=assign_now,
                        event_fk=event
                    )
                    remaining -= assign_now
                if remaining == 0:
                    break

        # 5) máscara subida (opcional)
        mask_file = form.cleaned_data.get("mask_image")
        if mask_file:
            dest_path = save_event_mask(event.id, mask_file)
            updated = event.qr_codes.update(mask_banner=dest_path)
            messages.success(request, f"Máscara aplicada a {updated} QR(s) del evento '{event.name}'.")

        # 6) FREE con Ads → aplicar top banner/footer por país (auto)
        if free_with_ads:
            country_code = (form.cleaned_data.get("country_code") or "").strip() or getattr(request, "country_code", None)
            country_name = (form.cleaned_data.get("country_name") or "").strip() or getattr(request, "country_name", None)
            ad = None
            try:
                ad = get_banner_for_country(country_code, country_name)
            except Exception:
                ad = None

            preset = get_footer_preset(country_code, country_name)
            updates = {
                "enable_top_banner": True,
                "footer_text": preset["text"],
                "footer_bg": preset["bg"],
                "footer_fg": preset["fg"],
            }
            if ad and ad.image:
                updates["top_banner"] = ad.image.name
            updated = event.qr_codes.update(**updates)
            messages.success(request, f"Se aplicó publicidad por país y footer a {updated} QR(s).")

        # 7) re-render inmediato (opcional)
        if form.cleaned_data.get("re_render_now"):
            country_code = (form.cleaned_data.get("country_code") or "").strip() or getattr(request, "country_code", None)
            country_name = (form.cleaned_data.get("country_name") or "").strip() or getattr(request, "country_name", None)
            valid_from   = (form.cleaned_data.get("valid_from") or "").strip() or None
            valid_until  = (form.cleaned_data.get("valid_until") or "").strip() or None
            grace_minutes = form.cleaned_data.get("grace_minutes") or 0
            font_path    = (form.cleaned_data.get("font_path") or "").strip() or None

            qrs = event.qr_codes.only("id", "data")
            MAX_INLINE = 200
            count = 0
            for qr in qrs[:MAX_INLINE]:
                compose_qr_from_db(
                    qr,
                    country_code=country_code,
                    country_name=country_name,
                    valid_from_str=valid_from,
                    valid_until_str=valid_until,
                    grace_minutes=grace_minutes,
                    font_path=font_path,
                )
                count += 1
            remaining = max(qrs.count() - MAX_INLINE, 0)
            if remaining > 0:
                messages.info(request, f"Se regeneraron {count} imágenes. Quedan {remaining}. Usa la acción de Admin o Celery para lotes grandes.")
            else:
                messages.success(request, f"Re-render completado para {count} QR(s).")

        # 8) notificación por email (solo si NO es free, mantén tu lógica)
        if not free_with_ads:
            send_event_qr_codes.delay(event.id)

        origen = "gratis con Ads" if free_with_ads else "con tus tickets"
        messages.success(request, f"Evento '{event.name}' creado {origen}.")
        return redirect('dashboard:inicio')

    # GET sin cambios
    else:
        # form = AutoTicketAssignmentForm(user=user_id)
        # user_events = Event.objects.filter(created_by=user_id).annotate(
        #     recycled_count=Count('qr_codes', filter=Q(qr_codes__status_recycled='recycled'))
        # )
        # context = {'events': user_events, 'user': user_name, 'form': form}
        # return render(request, template, context)
        # === AUTOCOMPLETE desde AdPlacement ===
        detected_cc = getattr(request, "country_code", None)
        detected_cn = getattr(request, "country_name", None)
        ad = None
        try:
            ad = get_banner_for_country(detected_cc, detected_cn)
        except Exception:
            ad = None

        # Si tu modelo AdPlacement incluye estos campos opcionales, los usamos:
        # - country (texto)
        # - starts_at, ends_at (DateTimeField)
        # - grace_minutes (IntegerField, opcional)
        # - font_path (CharField, opcional)
        initial = {}
        if ad:
            # country_code / country_name
            # Si tu modelo AdPlacement guarda solo "country" textual, úsalo para name y deja code al detectado
            initial["country_code"] = (detected_cc or "").strip()
            initial["country_name"] = (getattr(ad, "country", None) or detected_cn or "").strip()

            # Fechas: normalizamos a 'YYYY-MM-DDTHH:MM:SS' en UTC-4 o localtime (elige tu criterio)
            def to_iso_local(dt):
                if not dt:
                    return ""
                # Si manejas todo en UTC internamente, puedes usar dt.astimezone(...) a UTC-4
                # Aquí usamos localtime por simplicidad; ajusta si prefieres zona fija
                return localtime(dt).strftime("%Y-%m-%dT%H:%M:%S")

            initial["valid_from"] = to_iso_local(getattr(ad, "starts_at", None))
            initial["valid_until"] = to_iso_local(getattr(ad, "ends_at", None))
            initial["grace_minutes"] = getattr(ad, "grace_minutes", 0) or 0
            initial["font_path"] = getattr(ad, "font_path", "") or ""

        # Si no hay AdPlacement, sugerimos el país detectado y dejamos lo demás vacío
        if not initial:
            initial = {
                "country_code": (detected_cc or "").strip(),
                "country_name": (detected_cn or "").strip(),
                "valid_from": "",
                "valid_until": "",
                "grace_minutes": 0,
                "font_path": "",
            }

        # IMPORTANTE: pásale initial y user al form
        form = AutoTicketAssignmentForm(user=user_id, initial=initial)

        user_events = Event.objects.filter(created_by=user_id).annotate(
            recycled_count=Count('qr_codes', filter=Q(qr_codes__status_recycled='recycled'))
        )
        context = {'events': user_events, 'user': user_name, 'form': form}
        return render(request, template, context)

################################################
#   Vista de QR zip and download
################################################
def download_qr_zip(request, event_id):
    """Generates a ZIP file containing all QR codes for a given event."""
    event = get_object_or_404(Event, id=event_id)
    qr_codes = event.qr_codes.all()
    if not qr_codes.exists():
        return HttpResponse("No QR codes available for this event.", status=404)

    # Create an in-memory ZIP file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for qr in qr_codes:
            if qr.image:
                file_path = qr.image.path
                file_name = os.path.basename(file_path)
                zip_file.write(file_path, file_name)

    zip_buffer.seek(0)

    # Send ZIP as a downloadable response
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="QR_{event.name}.zip"'
    return response


################################################
#   Pagina de QR update event form db
################################################
def updatedb(request, pk):
    event = get_object_or_404(Event, id=pk)
    user_name = request.user
    if request.method == "POST":
        form = UpdateQRCodesForm(request.POST, instance=event)
        if form.is_valid():
            new_total_qr_count = form.cleaned_data["new_qr_code_count"]
            event.update_qr_codes(new_total_qr_count)  # Call the method from the model
            messages.success(request, f"QR codes updated to {new_total_qr_count}.")

            url = reverse('dashboard:create_checkout_session', kwargs={'pk': 1, 'slug': pk })
            return redirect(url)
    else:
        form = UpdateQRCodesForm(instance=event, initial={"new_qr_code_count": event.qr_code_count})

    return render(request, "dashboard/update_event.html", {"form": form, "event": event,'user':user_name})

################################################
#   Pagina de QR create event form db
################################################
def createdb(request):
    template = 'dashboard/create-db.html' 
    user_name = request.user
    product1 = Product.objects.get(name="Plan 1")
    product2 = Product.objects.get(name="Plan 2")
    product3 = Product.objects.get(name="Plan 3")
    print(product1.id)
    # print(request.POST['solicitud'])
    context = {
        "product1": product1,
        "product2": product2,
        "product3": product3, 
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        'solicitud': int(request.GET.get('solicitud')),
        'user':user_name
        }
    print(request.GET.get('solicitud'))
    if request.method == "POST" :
        name = request.POST["name"]
        qr_code_count_post = request.POST["qr_code_count"]
        image = request.FILES.get("image")
        print(image)
        if image:
            image_save = Image.open(io.BytesIO(image.read()))
        else:
            # Crear una imagen blanca por defecto (500x500 px)
            image_save = Image.new('RGB', (330, 330), color='white')
        # image_save = Image.open(io.BytesIO(image.read()))
        print(image_save)
        buffer = io.BytesIO()
        image_save.save(buffer, format="jpeg")
        buffer.seek(0)
        temp_image_file = InMemoryUploadedFile(
            buffer, None, "temp_image.png", "image/png", sys.getsizeof(buffer), None
        )
        
        #
        event = Event.objects.create(
            name=name,
            created_by=request.user,
            qr_code_count = int(qr_code_count_post),
            image=temp_image_file
        )
        url = reverse('dashboard:create_checkout_session', kwargs={'pk': product1.id, 'slug': event.id })
        return redirect(url)
    return render(request, template, context)
################################################
#   Pagina de QR assign assign
################################################
def assign(request):
    user_name = request.user
    template = 'dashboard/assign.html' 
    user_id = request.user.id
    user_events = Event.objects.filter(created_by=user_id)
    qr_codes_list = [qr for event in user_events for qr in event.qr_codes.all()]
    
    print(qr_codes_list)
    
    if request.method == 'POST':
        qr = QRCode.objects.get(id=request.POST["id"])  # Get the qr id to update
        form = UserEmailForm(request.POST)
        if form.is_valid():
            qr.email = request.POST['user_email']  # Update the user's email
            qr.save()
            return redirect('dashboard/assign.html')  # Redirect after successful update

    context = {'qr': qr_codes_list, 'user':user_name}
    return render(request, template, context)


################################################
#   Pagina de QR assign assign update email
################################################
def update_user_email(request, id):
    qr = QRCode.objects.get(id=id)  # Get the qr id to update
    user_name = request.user
    if request.method == 'POST':
        form = UserEmailForm(request.POST)
        if form.is_valid():
            qr.email = form.cleaned_data['email']  # Update the user's email
            qr.save()
            return redirect('dashboard/assign.html')  # Redirect after successful update
    else:
        form = UserEmailForm(initial={'email': qr.email})
    user_id = request.user.id
    user_events = Event.objects.filter(created_by=user_id)
    qr_codes_list = [qr for event in user_events for qr in event.qr_codes.all()]
    context = {'qr': qr_codes_list, 'user':user_name}
    return render(request, 'dashboard/assign.html', context)
################################################
#   Pagina de QR basic
################################################
def basic(request):
    template = 'dashboard/basic.html'    
    context = {}
    return render(request, template, context)
################################################
#   Pagina de QR tables
################################################
def tables(request):
    template = 'dashboard/tables.html' 
    context = {}
    return render(request, template, context)

################################################
#   Pagina de pagos
################################################
@csrf_exempt
def create_checkout_session(request, pk):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    ticket = get_object_or_404(Ticket, id=pk, is_paid=False)
    price_per_ticket = ticket.get_price_tier().price_cents
    total_cents = price_per_ticket * ticket.quantity
    Payments = Payment.objects.create(
            ticket = ticket,
            payment_method = 'card'
        )
    print('checkout session init')
    YOUR_DOMAIN = "https://app.manillasbolivia.com/"
    
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': price_per_ticket,
                    'product_data': {
                        'name': f"{ticket.quantity} Tickets for {ticket.user_name}",
                    },
                },
                'quantity': ticket.quantity,
            },
        ],
        metadata={
            "product_id": ticket.id,
        },
        mode='payment',
        # Modificar
        success_url=YOUR_DOMAIN + '/dashboard/success',
        cancel_url=YOUR_DOMAIN + '/dashboard/cancel',
    )

    # send_event_qr_codes.delay(Eventid.id)
    return redirect(checkout_session.url, code=303)
    # return JsonResponse({'error': 'Invalid request method'}, status=400)
################################################
#   Pagina de pagos ok
################################################

class SuccessView(TemplateView):
    template_name = "dashboard/success.html"

################################################
#   Pagina de pagos cancel
################################################
class CancelView(TemplateView):
    template_name = "dashboard/cancel.html"

################################################
#   Pagina de Terminos y condiciones
################################################
def qr_app(request):
    template = 'dashboard/qrapp.html'
    return render(request, template, )

################################################
#   Pagina de Terminos y condiciones APK 2
################################################
def qr_app2(request):
    template = 'dashboard/qrapp2.html'
    return render(request, template, )
################################################
#   Geotest
################################################
def geo_test(request):
    return JsonResponse({
        "ip": request.META.get("REMOTE_ADDR"),
        "country_code": getattr(request, "country_code", None),
        "country_name": getattr(request, "country_name", None),
    })