from django.db import models

# TODO: Andrew - Can you tell Grace if these model databases are saved in the same format on Postgre?
# I want to see if they save the time made too for reach of the models; also would like to see how the id is made 
# Within postgre


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
    