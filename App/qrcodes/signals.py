# dashboard/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import EventInvite

User = get_user_model()

@receiver(post_save, sender=User)
def assign_events_on_signup(sender, instance, created, **kwargs):
    if created:
        pending_invites = EventInvite.objects.filter(email=instance.email, accepted=False)
        for invite in pending_invites:
            invite.event.shared_with.add(instance)
            invite.accepted = True
            invite.save()
