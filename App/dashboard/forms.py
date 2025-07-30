from django import forms
from qrcodes.models import QRCode, Event, Ticket, TicketAssignment

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
        queryset=Event.objects.none(),  # inicial vacío
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Select Event",
        empty_label="Choose one of your events...",
    )


    def __init__(self, *args, user=None, events=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Si llega lista de eventos (invitado), limitémosla:
        if events is not None:
            self.fields['event'].queryset = Event.objects.filter(
                id__in=[e.id for e in events]
            ).order_by('-date')
        # Si no, pero hay user: eventos propios (comprador)
        elif user:
            self.fields['event'].queryset = (
                Event.objects.filter(created_by=user)
                             .order_by('-date')
            )

class InviteForm(forms.Form):
    email = forms.EmailField(label="Guest email")

class AutoTicketAssignmentForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, label="Number of QRs to assign")

    class Meta:
        model = TicketAssignment
        fields = ['event', 'quantity']
        widgets = {
            'event': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Events name'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'event': 'Events name',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Pasaremos el user desde la vista
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.user:
            tickets = Ticket.objects.filter(user_name=self.user, is_paid=True)
            total_unassigned = sum(t.unassigned_quantity() for t in tickets)
            if quantity > total_unassigned:
                raise forms.ValidationError(f"Tienes solo {total_unassigned} tickets disponibles.")
        return quantity
    

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