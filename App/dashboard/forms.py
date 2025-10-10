from django import forms
from qrcodes.models import QRCode, Event, Ticket, TicketAssignment
from django.core.exceptions import ValidationError

class UserEmailForm(forms.ModelForm):
    class Meta:
        model = QRCode
        fields = ['user_email']

class ShareQRCodeForm(forms.Form):
    recipient_email = forms.EmailField(label="Recipient Email")
    number_of_codes   = forms.IntegerField(
        label="Number of QR Codes to Share",
        min_value=1
    )

class EventUpdateForm(forms.Form):
    class Meta:
        model = Event
        fields = ['name','qr_code_count','image']

class UpdateQRCodesForm(forms.ModelForm):
    new_qr_code_count = forms.IntegerField(
        min_value=1,
        label="New QR Code Count",
        help_text="Enter the total number of QR codes for this event."
    )

    class Meta:
        model = Event
        fields = []

    def clean_new_qr_code_count(self):
        """Ensure the new QR count is greater than the existing count."""
        new_count = self.cleaned_data.get("new_qr_code_count")
        event = self.instance  # The event being updated
        if new_count < event.qr_code_count:
            raise forms.ValidationError("New count must be greater than the existing QR count.")
        return new_count
    
class MyPostForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['quantity']  # Only include quantity
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1, 'class': 'form-control'}),
        }
        labels = {
            'quantity': 'quantity of qr codes',
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 1:
            raise forms.ValidationError("The quantity must be greater than 0")
        return quantity

class TicketAssignmentForm(forms.ModelForm):
    class Meta:
        model = TicketAssignment
        fields = ['ticket', 'event', 'quantity']
        widgets = {
            'ticket': forms.Select(attrs={'class': 'form-control'}),
            'event': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'ticket': 'Ticket',
            'event': 'Event',
            'quantity': 'Quantity of QR codes to assign',
        }
    def clean(self):
        cleaned_data = super().clean()
        ticket = cleaned_data.get("ticket")
        quantity = cleaned_data.get("quantity")

        if ticket and quantity:
            unassigned = ticket.unassigned_quantity()
            if quantity > unassigned:
                raise forms.ValidationError(
                    f"The ticket only has {unassigned} unassigned tickets left."
                )
        return cleaned_data

class EventSelectorForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control mx-auto',
            'style': 'display:block; margin-left:auto; margin-right:auto; width:50%;'
        }),
        label="Select Event",
        empty_label="Choose one of your events...",
    )

    def __init__(self, *args, user=None, events=None, **kwargs):
        super().__init__(*args, **kwargs)
        if events is not None:
            self.fields['event'].queryset = Event.objects.filter(
                id__in=[e.id for e in events]
            ).order_by('-date')
        elif user:
            self.fields['event'].queryset = Event.objects.filter(
                created_by=user
            ).order_by('-date')
        # Agregar clase al label
        self.fields['event'].label_suffix = ''
        self.fields['event'].widget.attrs.update({'class': 'form-control mx-auto'})

class InviteForm(forms.Form):
    email = forms.EmailField(label="Guest email")

class AutoTicketAssignmentForm(forms.ModelForm):
    """
    Minimal form: only event name, quantity, and optional mask.
    Other decisions (free/paid, ads, country, dates) are handled by the view.
    """
    quantity = forms.IntegerField(
        min_value=1,
        required=True,
        label='',  # Hide label
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'placeholder': 'Number of QRs'
        })
    )

    mask_image = forms.ImageField(
        required=False,
        label="Central mask (720x1150 optional)",
        help_text="PNG/JPG; normalized to 720x1150."
    )

    class Meta:
        model = TicketAssignment
        fields = ['event', 'quantity', 'mask_image']
        widgets = {
            'event': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Event name'
            }),
        }
        labels = {
            'event': '',  # Hide label for event
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_event(self):
        name = self.cleaned_data['event']
        return name.strip()
# class AutoTicketAssignmentForm(forms.ModelForm):
#     # Hacemos event requerido explícitamente
#     event = forms.CharField(
#         required=True,
#         label="Events name",
#         widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Events name'})
#     )

#     quantity = forms.IntegerField(
#         min_value=1,
#         label="Number of QRs to assign",
#         widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
#     )

#     # Modo gratis con Ads
#     free_with_ads = forms.BooleanField(
#         required=False,
#         label="Crear gratis con publicidad",
#         help_text="Usará tu saldo de tickets FREE (con Ads)."
#     )

#     # Subir máscara central (opcional)
#     mask_image = forms.ImageField(
#         required=False,
#         label="Máscara (720x1150)",
#         help_text="PNG/JPG. Se normaliza a 720x1150 en el servidor."
#     )

#     # Re-render inmediato (limitado)
#     re_render_now = forms.BooleanField(required=False, initial=False, label="Re-render ahora")

#     # País (rellenados automáticamente si hay AdPlacement o middleware)
#     country_code = forms.CharField(required=False, max_length=8, label="Country code (ej. BO)")
#     country_name = forms.CharField(required=False, max_length=64, label="Country name (ej. Bolivia)")

#     # Estos campos los espera la vista para componer QR (pueden ir ocultos)
#     valid_from = forms.CharField(required=False, widget=forms.HiddenInput())
#     valid_until = forms.CharField(required=False, widget=forms.HiddenInput())
#     grace_minutes = forms.IntegerField(required=False, min_value=0, widget=forms.HiddenInput())
#     font_path = forms.CharField(required=False, widget=forms.HiddenInput())

#     class Meta:
#         model = TicketAssignment
#         fields = ['event', 'quantity']  # los demás son no-model fields

#     def __init__(self, *args, **kwargs):
#         # La vista debe pasar user=request.user
#         self.user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)

#     # ---------- Helpers ----------
#     def _user_id(self):
#         # soporta user o user.id ya que la vista a veces pasa el id
#         return getattr(self.user, 'id', self.user)

#     def _unassigned_sum(self, tickets_qs):
#         # Suma con la misma regla de negocio que ya usas
#         return sum(t.unassigned_quantity() for t in tickets_qs)

#     # ---------- Validaciones ----------
#     def clean_mask_image(self):
#         file = self.cleaned_data.get('mask_image')
#         if not file:
#             return file
#         # Validación básica de imagen + reposicionar puntero
#         content_type = (getattr(file, "content_type", "") or "").lower()
#         if not (content_type.startswith("image/")):
#             raise ValidationError("El archivo de máscara debe ser una imagen válida.")

#         # Tamaño máximo opcional (p.ej. 8MB)
#         max_mb = 8
#         if getattr(file, "size", 0) > max_mb * 1024 * 1024:
#             raise ValidationError(f"El archivo excede {max_mb}MB.")

#         # Verifica que PIL pueda abrirla (sin consumir el stream)
#         pos = file.tell() if hasattr(file, "tell") else 0
#         try:
#             from PIL import Image
#             img = Image.open(file)
#             img.verify()  # valida encabezado
#         except Exception:
#             raise ValidationError("La máscara está corrupta o no es una imagen soportada.")
#         finally:
#             try:
#                 file.seek(pos)  # MUY IMPORTANTE: reset para que la vista la pueda leer
#             except Exception:
#                 pass

#         return file

#     def clean(self):
#         cleaned = super().clean()

#         # event requerido
#         ev = (cleaned.get('event') or "").strip()
#         if not ev:
#             self.add_error('event', "El nombre del evento es obligatorio.")

#         qty = cleaned.get('quantity') or 0
#         free_mode = bool(cleaned.get('free_with_ads'))

#         uid = self._user_id()
#         if uid is None:
#             # Si por alguna razón no tenemos user id, bloquea
#             raise ValidationError("No se pudo identificar al usuario.")

#         if free_mode:
#             # Tickets FREE con Ads
#             free_tickets = Ticket.objects.filter(
#                 user_name=uid,
#                 plan='free',
#                 ads_enabled=True
#             )
#             available_free = self._unassigned_sum(free_tickets)
#             if qty > available_free:
#                 self.add_error(
#                     'quantity',
#                     f"No tienes suficientes tickets FREE con Ads. Disponibles: {available_free}."
#                 )
#         else:
#             # Tickets pagados
#             paid_tickets = Ticket.objects.filter(
#                 user_name=uid,
#                 is_paid=True
#             )
#             available_paid = self._unassigned_sum(paid_tickets)
#             if qty > available_paid:
#                 self.add_error(
#                     'quantity',
#                     f"Tienes solo {available_paid} tickets pagados sin asignar. "
#                     f"Activa 'Crear gratis con publicidad' si deseas usar tu saldo FREE."
#                 )

#         return cleaned


# class AutoTicketAssignmentForm(forms.ModelForm):
#     quantity = forms.IntegerField(min_value=1, label="Number of QRs to assign")

#     # Nuevo: modo gratis con Ads
#     free_with_ads = forms.BooleanField(
#         required=False,
#         label="Crear gratis con publicidad",
#         help_text="Permite crear el evento aunque no tengas tickets disponibles."
#     )

#     # Nuevo: subir máscara central
#     mask_image = forms.ImageField(
#         required=False,
#         label="Máscara (720x1150)",
#         help_text="PNG/JPG. Se normaliza a 720x1150."
#     )

#     # Nuevo: re-render inmediato (limitado)
#     re_render_now = forms.BooleanField(required=False, initial=False, label="Re-render ahora")
#     country_code = forms.CharField(required=False, max_length=8, label="Country code (ej. BO)")
#     country_name = forms.CharField(required=False, max_length=64, label="Country name (ej. Bolivia)")

#     class Meta:
#         model = TicketAssignment
#         fields = ['event', 'quantity']
#         widgets = {
#             'event': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Events name'}),
#             'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
#         }
#         labels = {
#             'event': 'Events name',
#         }

#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)  # Pasaremos el user desde la vista
#         super().__init__(*args, **kwargs)

 
#     def _get_user_id(self):
#         if hasattr(self.user, 'id'):
#             return self.user.id
#         return self.user

#     def clean_quantity(self):
#         qty = self.cleaned_data['quantity']
#         if self.cleaned_data.get('free_with_ads'):
#             return qty
#         uid = self._get_user_id()
#         if uid is not None:
#             tickets = Ticket.objects.filter(user_name=uid, is_paid=True)
#             total_unassigned = sum(t.unassigned_quantity() for t in tickets)
#             if qty > total_unassigned:
#                 raise forms.ValidationError(f"Tienes solo {total_unassigned} tickets disponibles.")
#         return qty

#     def clean_mask_image(self):
#         f = self.cleaned_data.get('mask_image')
#         if not f:
#             return f
#         max_mb = 5
#         if hasattr(f, 'size') and f.size > max_mb * 1024 * 1024:
#             raise forms.ValidationError(f"La imagen excede {max_mb} MB.")
#         if hasattr(f, 'content_type') and f.content_type not in ('image/png', 'image/jpeg', 'image/jpg'):
#             raise forms.ValidationError("Formato no soportado. Usa PNG o JPG.")
#         return f
    
class EventRecycleForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        widget=forms.HiddenInput(),  # 🔒 Hidden: can't be changed in UI
        label="",
        required=True
    )

    recycle_confirm = forms.ChoiceField(
        choices=[('yes', 'Sí, deseo reciclar los códigos'), ('no', 'No, cancelar')],
        widget=forms.RadioSelect,
        label="¿Deseas reciclar los códigos QR disponibles de este evento?"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        event_id = kwargs.pop('event_id', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['event'].queryset = Event.objects.filter(created_by=user)

        if event_id:
            try:
                self.fields['event'].initial = Event.objects.get(id=event_id, created_by=user)
            except Event.DoesNotExist:
                pass


class PrintQRForm(forms.Form):
    quantity = forms.IntegerField(
        label="How many QR codes to print",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, available_count, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limitar el valor máximo al número de QR disponibles
        self.fields['quantity'].max_value = available_count
        self.fields['quantity'].widget.attrs.update({'max': available_count})
        self.fields['quantity'].help_text = f"Available: {available_count}"