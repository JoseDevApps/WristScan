from django import forms
from qrcodes.models import QRCode, Event

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
