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
from django.contrib.auth import logout

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
#   Compartir QR
################################################
def share_qr_codes(request):
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = ShareQRCodeForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.cleaned_data['event']
            recipient_email = form.cleaned_data['recipient_email']
            number_of_codes = form.cleaned_data['number_of_codes']

            available_qr_codes = event.qr_codes.filter(status_purchased='available')[:number_of_codes]
            available_count = available_qr_codes.count()

            if available_count < number_of_codes:
                form.add_error('number_of_codes', f'Only {available_count} QR codes are available.')
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    codes_shared = []
                    for qr_code in available_qr_codes:
                        print('start updating')
                        qr_code.status_purchased = 'purchased'
                        qr_code.user_email = recipient_email
                        qr_code.save()
                        qr_code_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes/', f"qr_{qr_code.id}_.png")
                        print(qr_code_path)
                        print(qr_code.id)
                        if os.path.exists(qr_code_path):
                            print("zip files")
                            print(qr_code.data)
                            zip_file.write(qr_code_path, f"qr_{qr_code.id}_.png")
                        codes_shared.append(qr_code.data)
                zip_buffer.seek(0)
                # Send email to the recipient
                subject = f"QR Codes for Event: {event.name}"
                message = f"You have been granted access to the event: {event.name}\n\n" \
                          f"Attached are your {number_of_codes} QR codes."

                email = EmailMessage(
                    subject,
                    message,
                    'minusmaya@zohomail.com',
                    [recipient_email]
                )
                email.attach(f"{event.name}_QR_Codes.zip", zip_buffer.getvalue(), "application/zip")
                email.send()

                return render(request, 'dashboard/share_confirmation.html', {
                    'event': event,
                    'recipient_email': recipient_email,
                    'codes_shared': codes_shared,
                    'remaining_codes': event.qr_codes.filter(status_purchased='available').count()
                })
    else:
        form = ShareQRCodeForm(user=request.user)

    return render(request, 'dashboard/shareqr.html', {'form': form})

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
            "QR ID": qr.id,
            "QRCode": qr.data,
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
    available_codes_count = paid_tickets_total - total_qr_purchased_by_user + total_qr_recycled_by_user
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
    # if form.is_valid():
    #         ticket = form.save(commit=False)
    #         ticket.user_name = user_name if hasattr(user_name, 'email') else str(user_name)
    #         ticket.save()
    if request.method == "POST":
        ticket_db = Ticket.objects.create(
            user_name = user_name,
            quantity = request.POST["quantity"],
            is_paid = False
        )
        url = reverse('dashboard:create_checkout_session', kwargs={'pk': ticket_db.id })
        return redirect(url)
    print(user_events)
    context = {'user':user_name, "NC":str(len(qr_codes_list)), "NE":str(len(user_events)), "purchased":events_with_purchased_qr_count, 'tp':total_qr_purchased_by_user,
               'available':available_codes_count,'used':total_qr_used_by_user,
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
    user_name = request.user
    form = EventSelectorForm(user=request.user)
    websocket_url = 'wss://app.manillasbolivia.com/ws/qr/'  # You can dynamically set this URL
    return render(request, 'dashboard/qrscan.html', {'websocket_url': websocket_url, 'user':user_name,'form':form})
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

################################################
#   Pagina de QR view events form db
################################################
def listdb(request):
    template = 'dashboard/tables_event.html'
    user_name = request.user
    user_id = request.user.id

    
    form = AutoTicketAssignmentForm(user=request.user)
    if request.method == "POST":
        form = AutoTicketAssignmentForm(request.POST, user=request.user)
        # ticket = get_object_or_404(Ticket, id=int(request.POST['ticket']))
        # if form.is_valid():
        event_name = form.cleaned_data['event']
        quantity_to_assign = form.cleaned_data['quantity']

        # 1️⃣ Verificar si hay suficientes tickets disponibles
        tickets = Ticket.objects.filter(user_name=user_id, is_paid=True)
        total_unassigned = sum(t.unassigned_quantity() for t in tickets)

        if total_unassigned < quantity_to_assign:
            messages.error(request, f"Tienes solo {total_unassigned} tickets no asignados. No se puede crear el evento.")
            context = {'events': user_events, 'user':user_name,'form':form}
            return render(request, template, context)
            # return render(request, 'tickets/auto_assign_form.html', {'form': form})

        # 2️⃣ Crear imagen temporal en blanco
        image_save = Image.new('RGB', (300, 300), color='white')
        buffer = io.BytesIO()
        image_save.save(buffer, format="jpeg")
        buffer.seek(0)
        temp_image_file = InMemoryUploadedFile(
            buffer, None, "temp_image.png", "image/png", sys.getsizeof(buffer), None
        )

        # 3️⃣ Crear evento
        event = Event.objects.create(
            name=event_name,
            created_by=user_id,
            qr_code_count=quantity_to_assign,
            image=temp_image_file
        )

        # 4️⃣ Asignar a tickets disponibles
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

        # 5️⃣ Enviar códigos QR
        send_event_qr_codes.delay(event.id)

        messages.success(request, f"Se asignaron {quantity_to_assign} códigos QR al evento '{event.name}' correctamente.")
        return redirect('dashboard:inicio')
        # else:
        #     messages.error(request, "Corrige los errores del formulario.")
    else:
        form = AutoTicketAssignmentForm(user=user_id)
    #         ticket_assignment = TicketAssignment.objects.create(
    #           ticket = ticket,
    #           event = request.POST['event'],
    #           quantity = int(request.POST['quantity'])
    #         )
    #         messages.success(request, f"Successfully assigned {request.POST['quantity']} tickets to event '{request.POST['event']}'.")
    #         new_event_id = ticket_assignment.event_fk.id
    #         send_event_qr_codes.delay(new_event_id)
    #         return redirect('dashboard:inicio')  # Ajusta a tu URL
    #     else:
    #         messages.error(request, "Please correct the errors below.")
    # else:
    #     form = TicketAssignmentForm()
    user_events = Event.objects.filter(created_by=user_id)

    context = {'events': user_events, 'user':user_name,'form':form}
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