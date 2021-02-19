from django.db import models

# Create your models here.

class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides selfupdating ``created`` and ``modified`` fields.
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class User(TimeStampedModel):
    id = models.AutoField(primary_key=True)
    firstName = models.CharField(max_length=200)
    lastName = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    email = models.EmailField(unique=True)

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

class Eligibility(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    # May want to change options for married later
    rent = models.BooleanField()
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


class programs(TimeStampedModel):
    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    # These two fields have to be entered in after the verification of the documents
    snap = models.BooleanField()
    freeReducedLunch = models.BooleanField()
    