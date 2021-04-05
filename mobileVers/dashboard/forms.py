from django import forms
from .models import Form, Feedback

 
class FileForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = ['document_title','document','TaxBoxAmount']
        labels  = { 
            'document_title':'Program', 
            'document':'Document Upload',
            'TaxBoxAmount':'Amount of Box 11',
        }



'''need to complete below , tie this and models.py to index.html stars rating'''
class FeedbackForm(forms.ModelForm):
    #starRating = forms.ChoiceField(widget=forms.RadioSelect(), label="starRating")
    feedbackComments = forms.CharField(max_length = 500, required=False) 
    starRating = forms.CharField(max_length=1, required=True)
    class Meta:
        model = Feedback
        fields = ['feedbackComments','starRating']
        labels  = { 
            'starRating':'Rating in Stars',
            'feedbackComments':'Feedback and Comments by Clients', 
        } 