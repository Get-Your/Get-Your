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
# Eligibility model class attached to user (will delete as user account is deleted too)
class Eligibility(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    rent = models.CharField(choices=choices, max_length=10)

    #TODO: possibly add field for how many total individuals are in the household
    dependents = models.IntegerField(100)
    DEqualified = models.BooleanField(default=False)
    GRqualified = models.BooleanField(default=False)
    RecreationQualified = models.BooleanField(default=False)
    #TODO 5/13/2021
    #insert other rebate flags here i.e.
    #xQualified = models.BooleanField(default=False)
    #utilitiesQualified = models.BooleanField(default=False)

    # Income Levels
    LOW = 'Below $19,800'
    MED = '$19,800 ~ $32,800'
    HIGH = 'Over $32,800'
    INCOME_LEVELS = (
        (LOW, 'Below $19,800'),
        (MED, '$19,800 ~ $32,800'),
        (HIGH, 'Over $32,800'),
    )
    grossAnnualHouseholdIncome = models.CharField(
        max_length=20,
        choices=INCOME_LEVELS,
        default=LOW,
    )

# Programs model class attached to user (will delete as user account is deleted too)
class programs(TimeStampedModel): #incomeVerificationPrograms
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    snap = models.BooleanField()
    freeReducedLunch = models.BooleanField()
    #1040 = models.BooleanField() TODO include for 1040 filechecking


class addressVerification(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    Identification = models.BooleanField()
    Utility = models.BooleanField()
    freeReducedLunch = models.BooleanField()

class zipCode(TimeStampedModel):
    zipCode = models.DecimalField(max_digits=5, decimal_places=0)    

class futureEmails(TimeStampedModel):
    email = models.EmailField(unique=True)
