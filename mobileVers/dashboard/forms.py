from django import forms
from .models import Form
 
class FileForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = ['document_title','document']
        labels  = { 
            'document_title':'Program', 
            'document':'Document Upload',
        }