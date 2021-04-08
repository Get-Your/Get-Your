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
    files = models.ManyToManyField('dashboard.Form', related_name="forms")

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
    #used to keep the USPS sanitized address (if available)
    sanitizedAddress =  models.CharField(max_length=200, blank=True, default="")
    sanitizedAddress2 =  models.CharField(max_length=200, blank=True, default="")
    sanitizedCity =  models.CharField(max_length=64, blank=True, default="")
    sanitizedState =  models.CharField(max_length=255, blank=True, default="")
    sanitizedZipCode = models.DecimalField(max_digits=5, blank=True, decimal_places=0,)    

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
    #need this for function in views.py after client uploads their dependent information
    qualified = models.BooleanField(default=False)

    # Income Levels
    LOW = 'Below $19,800'
    MED = '$19,800 ~ $32,800'
    HIGH = 'Over $32,800'
    four = '+1,000,000'
    INCOME_LEVELS = (
        (LOW, 'Below $19,800'),
        (MED, '$19,800 ~ $32,800'),
        (HIGH, 'Over $32,800'),
        (four, '+1,000,000'),
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


'''


AMI = area median income, based on number of people per household
30% AMI
1 100,000
2 200,000
3 300,000
4 400,000
5 ...
6 ...
7 ...
8 800,000

I'm a client and i'm going through the application, i have 4 dependents
which means that I must make $400,000 and under to qualify for this program

the secret sauce for the application to automatically qualify / disqualify
is the number of dependents in the household


*DISCLAIMER NOT REAL NUMBERS JUST USING FOR THEORY CRAFTING*

'''