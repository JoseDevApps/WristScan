# # dashboard/signals.py
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model
# from qrcodes.models import EventInvite

# User = get_user_model()

# @receiver(post_save, sender=User)
# def assign_events_on_signup(sender, instance, created, **kwargs):
#     if created:
#         pending_invites = EventInvite.objects.filter(email=instance.email, accepted=False)
#         for invite in pending_invites:
#             invite.event.shared_with.add(instance)
#             invite.accepted = True
#             invite.save()
# qrcodes/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from qrcodes.models import EventInvite, EventRole

User = get_user_model()

@receiver(post_save, sender=User)
def assign_events_on_signup(sender, instance, created, **kwargs):
    if not created:
        return

    # Buscamos invitaciones pendientes para este email
    pending_invites = EventInvite.objects.filter(
        email=instance.email,
        accepted=False
    )

    for invite in pending_invites:
        # Marcamos la invitación como aceptada
        invite.accepted = True
        invite.save(update_fields=['accepted'])

        # Creamos un rol de monitor para este usuario en el evento
        EventRole.objects.get_or_create(
            user=instance,
            event=invite.event,
            role='monitor'
        )

from django.db import transaction
from qrcodes.models import Event, QRCode
from qrcodes.utils.event_mask import event_mask_path
from qrcodes.utils.qr_render_db import compose_qr_from_db

@receiver(post_save, sender=Event, dispatch_uid="apply_mask_and_rerender_after_event_creation_v1")
def apply_mask_and_rerender_after_event_creation(sender, instance: Event, created, **kwargs):
    """
    Tras crear/guardar un Event, si existe una máscara precargada en ads/masks/event_<id>.png,
    apuntamos TODOS los QR del evento a esa máscara (mask_banner) y re-renderizamos un batch.
    """
    # Ejecutar sólo cuando el evento esté listo y sus QRs creados (tu save() ya los genera)
    def _apply_and_render():
        mask_path = event_mask_path(instance.id)
        # Bulk update: actualiza mask_banner para TODOS los QRs del evento.
        instance.qr_codes.update(mask_banner=mask_path)

        # Re-render en línea (límite para no bloquear la request de quien creó el evento)
        MAX_INLINE = 200
        qs = QRCode.objects.filter(event__id=instance.id).only("id", "data")[:MAX_INLINE]
        for qr in qs:
            # Si quieres pasar país/fechas/TTF, añade kwargs:
            # compose_qr_from_db(qr, country_code=..., valid_until_str=..., etc.)
            compose_qr_from_db(qr)

        # Si necesitas procesar el resto, sugiere hacerlo via acción de admin o Celery.

    # Esperar al commit para garantizar que M2M y QRs están disponibles
    transaction.on_commit(_apply_and_render)