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
    
class MyPostForm(forms.Form):
    email = forms.EmailField()
    amount = forms.IntegerField(min_value=1)