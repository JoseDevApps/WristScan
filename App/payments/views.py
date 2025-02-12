import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
# from qrcodes.models import Product, User, QRCode  # Adjust according to your models
from qrcodes.tasks import send_event_qr_codes
from django.shortcuts import render, redirect
stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # Handle successful payments
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Retrieve metadata to identify the user and product
        # event_id = session["metadata"].get("event_id")

       
        # Generate QR codes for the user after the successful payment
        
        # send_event_qr_codes.delay(event_id.id)
        # return redirect("event_detail", event_id=event.id)
        # return redirect("")

    return JsonResponse({"status": "success"}, status=200)