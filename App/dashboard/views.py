from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
import stripe
from django.views.generic import TemplateView
from .models import Product

################################################
#   Pagina de bienvenida
################################################
@login_required
def inicio(request):
    template = 'dashboard/index.html' 
    context = {}
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
    template = 'dashboard/qrscan.html' 
    context = {}
    return render(request, template, context)
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
#   Pagina de QR assign assign
################################################
def assign(request):
    template = 'dashboard/assign.html' 
    context = {}
    return render(request, template, context)
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
    if request.method == "POST":
        stripe.api_key = settings.STRIPE_SECRET_KEY
        print('checkout session init')
        product = get_object_or_404(Product, id=pk)
        YOUR_DOMAIN = "http://127.0.0.1"
        
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
                "product_id": product.id
            },
            mode='payment',
            # Modificar
            success_url=YOUR_DOMAIN + '/dashboard/success',
            cancel_url=YOUR_DOMAIN + '/dashboard/cancel',
        )
        
        return redirect(checkout_session.url, code=303)
    return JsonResponse({'error': 'Invalid request method'}, status=400)
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
