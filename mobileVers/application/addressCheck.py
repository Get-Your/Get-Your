# Andrew backend code for address check
# 2/23/2021 TODO:
# Streamline logic for going through CSV file - priority: medium
# Using USPS-API, incorporate returned address to clients' view via drop-down bar - priority: high

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
                broadcast_sms(phone_Number)
                return True
            else:
                counter = counter + 1
                if counter == 68:
                    broadcast_sms(phone_Number)
                    return False
                else:
                    continue
