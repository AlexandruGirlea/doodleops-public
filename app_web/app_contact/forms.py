from django import forms

from app_contact.models import Contact


class ContactForm(forms.ModelForm):

	class Meta:
		"""
		Form fields for Contact model. Non-Model fields Do Not Go in Meta.fields.
		"""
		model = Contact
		fields = ['name', 'email', 'message', 'type', ]
		widgets = {
			'name': forms.TextInput(attrs={'class': 'form-control'}),
			'email': forms.EmailInput(attrs={'class': 'form-control'}),
			'message': forms.Textarea(attrs={'class': 'form-control'}),
			'type': forms.Select(attrs={'class': 'form-control'}),
		}
