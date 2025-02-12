from django import forms
from qrcodes.models import QRCode

class UserEmailForm(forms.ModelForm):
    class Meta:
        model = QRCode
        fields = ['user_email']