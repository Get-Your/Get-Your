from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _


# 2/23/2021 @Grace - yes they do! When we setup the database engine to Postgre SQL when we re-migrate and whatnot, the models are
# automatically formatted in the Postgre SQL format, we need to set timezone in settings.py however! Using your old code as an
# example, IDs were automatically generated, they were created incrementally. I actually want to ask you about ID's since we're
# on the topic - should we set clients and their IDs based on when the account was created (i.e. sequentially)? Or do we want
# some kind of numbering system? Perhaps for now, for simplicities sake maybe we can just give ID's out sequentially?

# 3/3/2021 @Andrew - yes that would be good to implement in the future! Just not sure what the best method is to do that; but 
# definitely feel like this is something we should discuss later

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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    #id = models.AutoField(primary_key=True)    
    # TODO:@Grace check this and implement? 
    # phone = models.DecimalField(max_digits=10, decimal_places=0)

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
    n2n = models.BooleanField()

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

    # TODO: possibly add field for how many total individuals are in the household
    dependents = models.IntegerField(100)

    # Income Levels
    LOW = 'Below $30,000'
    MED = '$30,000 ~ $60,000'
    HIGH = 'Over $60,000'
    INCOME_LEVELS = (
        (LOW, 'Below $30,000'),
        (MED, '$30,000 ~ $60,000'),
        (HIGH, 'Over $60,000'),
    )
    grossAnnualHouseholdIncome = models.CharField(
        max_length=20,
        choices=INCOME_LEVELS,
        default=LOW,
    )

# Programs model class attached to user (will delete as user account is deleted too)
class programs(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    # TODO: Andrew/Grace - These two fields have to be entered in after the verification of the documents
    snap = models.BooleanField()
    freeReducedLunch = models.BooleanField()
    