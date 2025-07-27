from django import forms

from app_pages.models import SuggestNewFeature


class SuggestNewFeatureForm(forms.ModelForm):
	class Meta:
		model = SuggestNewFeature
		fields = ['feature_description',]
		widgets = {
			'feature_description': forms.Textarea(attrs={'class': 'form-control'}),
		}
