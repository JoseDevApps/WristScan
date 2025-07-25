from .forms import UserCreationFormWithEmail
from django.views.generic import CreateView
from django.views.generic.edit import UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django import forms
from django.contrib.auth import login
from django.shortcuts import redirect
from qrcodes.models import EventInvite, EventRole

# Create your views here.
# class SignUpView(CreateView):
#     form_class = UserCreationFormWithEmail
#     template_name = 'registration/signup.html'

#     def get_success_url(self):
#         return reverse_lazy('login') + '?register'   

#     def get_form(self, form_class=None):
#         form = super(SignUpView, self).get_form()
#         # Modificar en tiempo real
#         form.fields['username'].widget = forms.TextInput(
#             attrs={'class':'form-control mb-2', 'placeholder':'Nombre de usuario'})
#         form.fields['email'].widget = forms.EmailInput(
#             attrs={'class':'form-control mb-2', 'placeholder':'Dirección email'})
#         form.fields['password1'].widget = forms.PasswordInput(
#             attrs={'class':'form-control mb-2', 'placeholder':'Contraseña'})
#         form.fields['password2'].widget = forms.PasswordInput(
#             attrs={'class':'form-control mb-2', 'placeholder':'Repite la contraseña'})
#         return form
class SignUpView(CreateView):
    form_class = UserCreationFormWithEmail
    template_name = 'registration/signup.html'

    def get_success_url(self):
        # Si venimos con ?email=<invitado> redirige al escáner de invitados
        if self.request.GET.get('email'):
            return reverse_lazy('dashboard:qrscan_invited')
        # Sino, al dashboard principal para comprar tickets
        return reverse_lazy('dashboard:inicio')
    def form_valid(self, form):
        # Se ejecuta tras validación exitosa
        user = form.save()
        login(self.request, user)

        invite_email = self.request.GET.get('email')
        if invite_email:
            # Marcar invitaciones y dar rol de monitor
            invites = EventInvite.objects.filter(email=invite_email)
            for inv in invites:
                inv.accepted = True
                inv.save(update_fields=['accepted'])
                EventRole.objects.get_or_create(
                    user=user,
                    event=inv.event,
                    role='monitor'
                )
        return redirect(self.get_success_url())

    def get_form(self, form_class=None):
         form = super(SignUpView, self).get_form()
         # Modificar en tiempo real
         form.fields['username'].widget = forms.TextInput(
            attrs={'class':'form-control mb-2', 'placeholder':'Nombre de usuario'})
         form.fields['email'].widget = forms.EmailInput(
            attrs={'class':'form-control mb-2', 'placeholder':'Dirección email'})
         form.fields['password1'].widget = forms.PasswordInput(
            attrs={'class':'form-control mb-2', 'placeholder':'Contraseña'})
         form.fields['password2'].widget = forms.PasswordInput(
            attrs={'class':'form-control mb-2', 'placeholder':'Repite la contraseña'})
         return form