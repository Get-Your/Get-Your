from django.db import models
from application.models import User

# Create your models here.s

class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides selfupdating ``created`` and ``modified`` fields.
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Form(TimeStampedModel):
    user_id = models.ForeignKey(User, related_name ="UserFiles", on_delete=models.CASCADE)
    form_titles = (
        ('SNAP', 'SNAP'),
        ('Free and Reduced Lunch', 'Free and Reduced Lunch')
        )
    document_title = models.CharField(
        max_length=30,
        choices=form_titles,
    )
    document = models.FileField()

class TaxInformation(TimeStampedModel):
    user_id = models.OneToOneField(
    User,
    on_delete=models.CASCADE,
    primary_key=True,
    )
    TaxBoxAmount = models.DecimalField(max_digits=9, null=True, blank=True, decimal_places=2,)


class Feedback(TimeStampedModel):
    starRating = models.CharField(
        max_length = 1
    )
    feedbackComments = models.TextField(
        max_length=500
    )
    