from django.db import models

# TODO: Andrew - Can you tell Grace if these model databases are saved in the same format on Postgre?
# I want to see if they save the time made too for reach of the models; also would like to see how the id is made 
# Within postgre
# 2/23/2021 @Grace - yes they do! When we setup the database engine to Postgre SQL when we re-migrate and whatnot, the models are
# automatically formatted in the Postgre SQL format, we need to set timezone in settings.py however! Using your old code as an
# example, IDs were automatically generated, they were created incrementally. I actually want to ask you about ID's since we're
# on the topic - should we set clients and their IDs based on when the account was created (i.e. sequentially)? Or do we want
# some kind of numbering system? Perhaps for now, for simplicities sake maybe we can just give ID's out sequentially?


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
class User(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    firstName = models.CharField(max_length=200)
    lastName = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
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

# Eligibility model class attached to user (will delete as user account is deleted too)
class Eligibility(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    rent = models.BooleanField()
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
    