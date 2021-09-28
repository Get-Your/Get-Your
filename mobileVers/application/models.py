from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _

# Create custom user manager class (because django only likes to use usernames as usernames not email)
class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        
        #Create and save a SuperUser with the given email and password.
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


# Class to automatically save date data was entered into postgre
class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides selfupdating ``created`` and ``modified`` fields.
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True



# User model class
class User(TimeStampedModel,AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    phone_number = PhoneNumberField()
    files = models.ManyToManyField('dashboard.Form', related_name="forms")
    address_files = models.ManyToManyField('dashboard.residencyForm', related_name="residencyforms")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email  

# Addresses model attached to user (will delete as user account is deleted too)
class Addresses(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    address = models.CharField(max_length=200, default="")
    address2 = models.CharField(max_length=200, blank=True, default="")

    # Try to get past the things that should be the same for every applicant
    city = models.CharField(max_length=64, default="Fort Collins")
    state = models.CharField(max_length=2, default="CO")

    zipCode = models.DecimalField(max_digits=5, decimal_places=0)    
    
    isInGMA = models.BooleanField(null=True, default=None)
    hasConnexion = models.BooleanField(null=True, default=None)

choices = (
    ('Rent', 'Rent'),
    ('Own', 'Own')
)

class AMI(TimeStampedModel):
    """ Model class to store the Area Median Income values.
    
    Note that these values are separated by number in household.
    
    The 'active' field designates if the record is currently in use; only
    'active' records should be displayed in the webapp.
    
    """
    
    householdNum = models.CharField(max_length=15, primary_key=True)
    active = models.BooleanField()
    
    ami = models.IntegerField()
    
    def __str__(self):
        return str(self.householdNum)
    
class iqProgramQualifications(TimeStampedModel):
    """ Model class to store the IQ program qualifications.
    
    The program names specified here will be used in the remainder of the
    app's backend.
    
    """
    
    name = models.CharField(max_length=40, primary_key=True)
    percentAmi = models.DecimalField(max_digits=10, decimal_places=4)
    
    def __str__(self):
        return str(self.percentAmi)

# Eligibility model class attached to user (will delete as user account is deleted too)
class Eligibility(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    rent = models.CharField(choices=choices, max_length=10)

    #TODO: possibly add field for how many total individuals are in the household
    dependents = models.IntegerField(100, default=1)
    dependentsAge = models.IntegerField(100, default=0)
    DEqualified = models.CharField(max_length=20)
    GenericQualified = models.CharField(max_length=20)
    ConnexionQualified = models.CharField(max_length=20)
    GRqualified = models.CharField(max_length=20)
    RecreationQualified = models.CharField(max_length=20)
    #TODO 5/13/2021
    #insert other rebate flags here i.e.
    #xQualified = models.CharField(max_length=20)
    #utilitiesQualified = models.CharField(max_length=20)

    grossAnnualHouseholdIncome = models.CharField(max_length=20)    
    # Define the min and max Gross Annual Household Income as a fraction of 
    # AMI (which is a function of number of individuals in household)
    AmiRange_min = models.DecimalField(max_digits=5, decimal_places=4)
    AmiRange_max = models.DecimalField(max_digits=5, decimal_places=4)

# Programs model class attached to user (will delete as user account is deleted too)
class programs(TimeStampedModel): #incomeVerificationPrograms
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    snap = models.BooleanField()
    freeReducedLunch = models.BooleanField()
    Identification = models.BooleanField()
    form1040 = models.BooleanField()

class attestations(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    completeAttestation = models.BooleanField(default=False)
    localAttestation = models.BooleanField(default=False)


class addressVerification(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    #Identification = models.BooleanField()
    Utility = models.BooleanField()
    #freeReducedLunch = models.BooleanField()

class addressLookup(TimeStampedModel):
    address = models.CharField(max_length=100) 

class futureEmails(TimeStampedModel):
    connexionCommunication = models.BooleanField(default=True, blank=True)


