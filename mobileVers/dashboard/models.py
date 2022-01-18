from django.db import models
from application.models import User
import datetime

from django.core.validators import FileExtensionValidator

# Create your models here.


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides selfupdating ``created`` and ``modified`` fields.
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user_id.id, filename)


class Form(TimeStampedModel):
    user_id = models.ForeignKey(User, related_name ="UserFiles", on_delete=models.CASCADE)
    document = models.FileField(validators=[FileExtensionValidator(['pdf','jpg','png'],)], max_length=5000, upload_to=user_directory_path) #upload_to="mobileVers/uploads/" + str(datetime.date.today()) + "/" this uploads file to date and time of day
    form_titles = (
        ('SNAP', 'SNAP'),
        ('Free and Reduced Lunch', 'Free and Reduced Lunch'),
        ('1040 Form', '1040 Form'),
        ('Identification', 'Identification'),
        )
    document_title = models.CharField(
        max_length=30,
        choices=form_titles,
    )
    
    

class residencyForm(TimeStampedModel):
    user_id = models.ForeignKey(User, related_name ="UserResidencyFiles", on_delete=models.CASCADE, blank=False)
    form_titles = (
        ('Identification', 'Identification'),
        ('Utility', 'Utility'),
        ('Free and Reduced Lunch', 'Free and Reduced Lunch'),
        )
    document_title = models.CharField(
        max_length=30,
        choices=form_titles,
    )
    document = models.FileField(validators=[FileExtensionValidator(['pdf','jpg','png'],)],max_length=5000,  upload_to=user_directory_path)


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
    