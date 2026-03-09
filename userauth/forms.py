from django import forms
from django.contrib.auth.forms import UserCreationForm
from userauth.models import User, Visitor
from .models import StaffCheckInOut, generate_visitor_id

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"style": "padding:5px; border-width:1px; border-color:gray; width:300px; border-radius:7px;", "placeholder": "Username"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"style": "padding:5px; border-width:1px; border-color:gray; width:300px; border-radius:7px;", "placeholder": "Email Address"}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"style": "padding:5px; border-width:1px; border-color:gray; width:300px; border-radius:7px;", "placeholder": "Password"}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"style": "padding:5px; border-width:1px; border-color:gray; width:300px; border-radius:7px;", "placeholder": "Confirm Password"}))
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, widget=forms.Select(attrs={"style": "padding:5px; border-width:1px; border-color:gray; width:300px; border-radius:7px;"}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


class StaffCheckInOutForm(forms.ModelForm):
    class Meta:
        model = StaffCheckInOut
        fields = ['name', 'id_no', 'phone_no', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'id_no': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_no': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PreRegistrationForm(forms.ModelForm):
    class Meta:
        model = Visitor
        fields = ['name', 'email', 'phone', 'reason', 'host', 'scheduled_date', 'site']
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def save(self, commit=True):
        visitor = super().save(commit=False)
        visitor.status = 'scheduled'
        visitor.check_in = None
        if not visitor.visitor_id:
            visitor.visitor_id = generate_visitor_id("OGL")
        if commit:
            visitor.save()
        return visitor

class PreBookForm(forms.ModelForm):
    class Meta:
        model = Visitor
        fields = ['name', 'email', 'scheduled_date', 'venue','boardroom', 'reason', 'site', 'company']
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'venue': forms.Select(attrs={
                'id': 'venue-select',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
            'site': forms.Select(attrs={
                'id': 'site-select',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
            'boardroom': forms.Select(attrs={
                'id': 'boardroom-select',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 h-32'
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500'
            }),
        }

    def save(self, commit=True):
        visitor = super().save(commit=False)
        visitor.status = 'scheduled'
        visitor.visitor_id = generate_visitor_id("OGL")
        if commit:
            visitor.save()
        return visitor
