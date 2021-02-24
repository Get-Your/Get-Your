from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse



import csv
from usps import USPSApi, Address
from twilioIntegration import broadcast_sms

#address comparison function for finding if address is within N2N bounds
def addressCheck(address1, phone_Number):
    with open("compare.csv", "r") as csv_file:
        counter = 0
        csv_reader = csv.reader(csv_file, delimiter=',')
        for lines in csv_reader:
            column = lines[0] + " " + lines[1] + " " + lines[2]
            if address1 == column:
                print("street address match found")
                print(column)
                print(phone_Number)
                broadcast_sms(phone_Number)
                return HttpResponseRedirect(reverse("application:addressFound"))
            else:
                counter = counter + 1
                print("searching...")
                print(counter)
                if counter == 68:
                    print("street address not found")
                    print(phone_Number)
                    broadcast_sms(phone_Number)
                    return HttpResponseRedirect(reverse("application:addressNotFound"))
                else:
                    continue
