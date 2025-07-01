from django import forms
from qrcodes.models import QRCode, Event, Ticket, TicketAssignment

class UserEmailForm(forms.ModelForm):
    class Meta:
        model = QRCode
        fields = ['user_email']

class ShareQRCodeForm(forms.Form):
    event = forms.ModelChoiceField(queryset=Event.objects.none(), label="Select Event")
    recipient_email = forms.EmailField(label="Recipient Email")
    number_of_codes = forms.IntegerField(label="Number of QR Codes to Share", min_value=1)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['event'].queryset = Event.objects.filter(created_by=user)

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

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # extrae el usuario
        super().__init__(*args, **kwargs)

        if user:
            self.fields['event'].queryset = Event.objects.filter(created_by=user).order_by('-date')

 
class InviteForm(forms.Form):
    email = forms.EmailField(label="Guest\'s email")