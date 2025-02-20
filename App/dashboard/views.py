from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import stripe
import zipfile
import os
from django.urls import reverse
from django.views.generic import TemplateView
from .models import Product
from qrcodes.models import Event, EventRole, QRCode
from qrcodes.tasks import send_event_qr_codes
import tempfile
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from PIL import Image
import io
from io import BytesIO
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile
from .forms import UserEmailForm, ShareQRCodeForm
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
                        qr_code_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes/', qr_code.image)
                        print(qr_code_path)
                        print(qr_code.image)
                        if os.path.exists(qr_code_path):
                            print(qr_code.data)
                            zip_file.write(qr_code_path, f"{qr_code.data}_final.png")
                        codes_shared.append(qr_code.data)
                zip_buffer.seek(0)
                # Send email to the recipient
                subject = f"QR Codes for Event: {event.name}"
                message = f"You have been granted access to the event: {event.name}\n\n" \
                          f"Attached are your QR codes."

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
#   Pagina de bienvenida
################################################
@login_required
def inicio(request):
    template = 'dashboard/index.html' 
    user_name = request.user
    user_id = request.user.id
    user_events = Event.objects.filter(created_by=user_id)
    
    qr_codes_list = [qr for event in user_events for qr in event.qr_codes.all()]
    print(len(qr_codes_list))
    context = {'user':user_name, "NC":str(len(qr_codes_list)), "NE":str(len(user_events))}
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
    # websocket_url = 'ws://10.38.134.24:8080/ws/qr/'  # You can dynamically set this URL
    websocket_url = 'wss://app.manillasbolivia.com/ws/qr/'  # You can dynamically set this URL
    return render(request, 'dashboard/qrscan.html', {'websocket_url': websocket_url})

################################################
#   Pagina de QR create event
################################################
def create(request):
    template = 'dashboard/create.html' 
    product1 = Product.objects.get(name="Plan 1")
    product2 = Product.objects.get(name="Plan 2")
    product3 = Product.objects.get(name="Plan 3")
    print(product1.id)
    
    context = {
        "product1": product1,
        "product2": product2,
        "product3": product3, 
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY
        }
    return render(request, template, context)

################################################
#   Pagina de QR create event form db
################################################
def createdb(request):
    template = 'dashboard/create-db.html' 
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
        'solicitud': int(request.GET.get('solicitud'))
        }
    print(request.GET.get('solicitud'))
    if request.method == "POST" :
        name = request.POST["name"]
        qr_code_count_post = request.POST["qr_code_count"]
        image = request.FILES.get("image")
        print(image)
        image_save = Image.open(io.BytesIO(image.read()))
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

    context = {'qr': qr_codes_list}
    return render(request, template, context)


################################################
#   Pagina de QR assign assign update email
################################################
def update_user_email(request, id):
    qr = QRCode.objects.get(id=id)  # Get the qr id to update

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
    context = {'qr': qr_codes_list}
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
def create_checkout_session(request, pk, slug):
    # if request.method == "POST":
    stripe.api_key = settings.STRIPE_SECRET_KEY
    print('checkout session init')
    product = get_object_or_404(Product, id=pk)
    Eventid = get_object_or_404(Event, id=slug)
    YOUR_DOMAIN = "https://app.manillasbolivia.com/"
    
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': product.price,
                    'product_data': {
                        'name': product.name,
                    },
                },
                'quantity': 1,
            },
        ],
        metadata={
            "product_id": product.id,
        },
        mode='payment',
        # Modificar
        success_url=YOUR_DOMAIN + '/dashboard/success',
        cancel_url=YOUR_DOMAIN + '/dashboard/cancel',
    )

    send_event_qr_codes.delay(Eventid.id)
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
