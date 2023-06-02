# User Acceptance Testing Plan
Use this document for guidelines on UAT for new Get FoCo releases.

When an issue is found, use the [UAT bug template](https://github.com/Get-Your/Get-Your/issues/new?assignees=&labels=bug%2C+uat&projects=&template=uat-bug.md&title=) to submit the issue to the development team.

> Note that this document is intended to cover all sections, such as for major releases.

# Plan
For clearest results, each tester should go through this document in order, starting with [Home Page Test](#home-page-tests).

# Key
This testing is designed for all parties to execute the tests, however sections/bullets marked '**Admin**' will require database access, so there's no need for non-administrators to pay attention to those designations.

# Helpful testing notes
- Note that email addresses must be unique; a password manager (such as [LastPass](https://www.lastpass.com)) is helpful for creating multiple accounts
- The testing steps need to be verified for desktop and mobile versions - the two version are based on screen resolution, so making the desktop browser window small enough will suffice as a mobile-display verification
- On any page, try entering no text and ridiculous values in any and all inputs and ensure the outcome is expected (see [this tutorial](https://twitter.com/sempf/status/514473420277694465) for a guide)
- On any page with a 'back' arrow, test the functionality and ensure previously-entered data are populated on the resulting page (so the user doesn't have to enter it again)
- On any page with the option, test the 'save & logout' button functionality. Within the application process, you should be brought back to the same point you were in the application; once you've completed the application (i.e. made it to the Dashboard), this should bring you back to the Dashboard.

# Home page tests
- 'Available Income Eligible Programs' section
    - *Test:* Select each Learn More link
    - *Expected result:* Each link should open a new tab/window to the correct page
- 'Curious?' section
    - *Test:* Enter known addresses and select 'enter'. Be sure to include addresses inside and outside the GMA as well as addresses with and without Connexion service
    - *Expected result:* The correct message should be displayed for each known address
- 'Log In' link
    - *Test:* Log in with a user that has made it through the application
    - *Expected result:* The login should take you to the Dashboard

    ----

    - *Test:* Use the 'Forgot your Password?' link to attempt a password reset
    - *Expected result:* Your password is able to be reset
- 'Apply' link
    - Go to [Application Tests](#application-pages-and-tests)

# Application pages and tests
## 'Before we get started' page (/get_ready)
- *Test:* Verify accurate information
- *Expected result:* Accurate information

Select 'apply' - this leads to [Create an Account](#step-1-create-an-account-page-account).

## Step 1: 'Create an Account' page (/account)
- Enter account information
    - *Test:* Try invalid email addresses, phone numbers, passwords
    - *Expected result:* The system should notify for all invalid input and not resort to a 'Server Error' after clicking 'create'
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_user` table

> Note that the final email address and phone number entered here (before moving on to the next testing step) will be used for the final [communication sent page](#step-6-we-sent-you-an-email-and-a-text-page-broadcast), so it will be helpful to end on a real email address and real phone number.

Select 'create' - this should notify that your account has been created and leads to [Where do you live](#step-2-where-do-you-live-page-address).

## Step 2: 'Where do you live?' page (/address)
- Enter address (leave the 'mailing address' question as 'Yes')
    - *Test:* Enter slightly-incorrect and invalid addresses and click 'continue' after each
    - *Expected result:* The `/address_correction` page should be able to correct the slightly-incorrect addresses and should display a 'not found' message (rather than an error) for the invalid addresses
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_address` and `app_addressrd` tables. The data should not be stored until after an address is verified, at which point the address is stored in `app_addressrd` with its corresponding ID stored in `app_address` for *both* the `eligibility_address_id` and the `mailing_address_id`
- Enter an address to move forward with and select 'No' for the 'mailing address' question
    - *Test:* \<same tests as previous address\>
    - *Expected result:* \<same results as previous address\>
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_address` and `app_addressrd` tables. The data should not be stored until after an address is verified, at which point the each address is stored in `app_addressrd` with its corresponding ID stored in `app_address`; the first address has its ID as the `eligibility_address_id`; the mailing address is `mailing_address_id`

Select both addresses (or as many as are necesssary) in `/address_correction` to confirm - this leads to [Household information](#step-3-household-information-page-household).

## Step 3: Household information page (/household)
- Make a selection for rent/own
    - ***Admin** test:* Select various radio buttons
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_household` table
- Make a select for 'How long have you lived at this address?'
    - ***Admin** test:* Select various radio buttons
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_household` table
- Enter input in 'How many individuals are in your household?'
    - *Test:* Test any input including invalid values (e.g. text, negative numbers)
    - *Expected result:* You should be notified on this page if a value in invalid
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_household` table

Select 'continue' - this leads to [Household member information](#step-3b-names-and-birthdates-of-household-members-household_members).

## Step 3b: Names and birthdates of household members (/household_members)
- Enter 'first and last name' for each individual
    - *Test:* Try to invalidate the form
    - *Expected result:* There shouldn't be any errors. As of v2.0.0, there isn't any logic behind this text box, so it shouldn't be able to be broken
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_householdmembers` table
    
- Enter birthdate for each individual
    - *Test:* Try invalid birthdates
    - *Expected result:* There shouldn't be any errors. As of v2.0.0, there isn't any logic behind the birthdate input
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_householdmembers` table

Select 'continue' - this leads to [Eligibility Programs](#step-4-are-you-currently-enrolled-in-any-of-the-following-page-programs).

## Step 4: 'Are you currently enrolled in any of the following' page (/programs)
- Select any combination of programs
    - *Test:* Test any combination of selected programs
    - *Expected result:* The selected combination should be displayed on the next 'file upload' page (the back arrow on the 'file upload' page will return you to the program-selection page)
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_eligibilityprogram` table. There should be a record for each program under the applicant's `user_id`, with each `program_id` reflecting the selected program(s)

Enter the final combination of programs and select 'continue' - this leads to [File Upload](#step-5-file-upload-page-files).

## Step 5: File upload page (/files)
- Upload file for each program (approved file types are PDF, PNG, or JPEG)
    - *Test:* Try uploading multiple files, non-approved file types, non-approved file types that are renamed to approved extensions. Do this for any program in the dropdown and try changing the dropdown value
    - *Expected result:* The platform should keep track of what programs have already had files uploaded and display a message when you attempt to submit non-approved file types
    - ***Admin** expected result:* Verify that the data are stored properly in the `app_eligibilityprogram` table. Each record from the [Eligibility Programs](#step-4-are-you-currently-enrolled-in-any-of-the-following-page-programs) section should have `document_path` filled with the path to the filename. Also verify that each file is stored at the specified path in Azure Blob Storage.

Select 'continue' after each upload - after uploading for all programs, this leads to [Communication Sent](#step-6-we-sent-you-an-email-and-a-text-page-broadcast).

## Step 6: 'We sent you an email and a text' page (/broadcast)
- *Test:* Verify the email and text came through, check that the 're-send' link works
- *Expected result:* The email and text should have been sent to the email address and phone number used to [create your account](#step-1-create-an-account-page-account). The email should be sent again each time the 're-send' link is selected (as of v2.0.0, this doesn't affect the text message)

Select 'continue' - this leads to the [Dashboard](#dashboard).

## Dashboard
- Ensure the 'congrats on creating an account' popup only displays the first time you get to your dashboard

For the following verifications, note that program qualification (for v2.0.0) depends on the entered address being within the GMA. The income threshold is the minimum of the selected [Eligibility Programs](#step-4-are-you-currently-enrolled-in-any-of-the-following-page-programs).

- *Test:* Verify that the 'programs you may qualify for' section has the expected programs
- *Expected result:* The expected programs are displayed (based on whether the non-mailing address is in the GMA and the minimum income threshold of the [Eligibility Programs](#step-4-are-you-currently-enrolled-in-any-of-the-following-page-programs))

----

- *Test:* Select 'Apply Now' for various programs
- *Expected result:* The page this leads to should display the expected message for the program you applied for, the button at the bottom should lead back to the Dashboard, and the program you selected should move to the 'pending approval' section

----

- *Test:* Verify that the 'pending approval' section has the expected programs
- *Expected result:* This is either programs you have applied for (via the 'Apply Now' button) or that have auto-apply enabled

----

- *Test:* Verify that the 'programs active' section has the expected programs
- *Expected result:* The only programs that should show here are once the admin enrolls the user

----

- ***Admin** test:* For the logged-in user, alter the apply/enroll status for each program (in the `app_iqprogram` table, toggle `is_enrolled` to flip apply/enroll status; remove the record for the program to remove the 'applied' status).
- ***Admin** expected result:* Verify that the expected outcomes are reflected on the user's Dashboard (on page refresh)

----

- *Test:* Verify the links in the 'City News' section
- *Expected result:* This section should give the expected information and lead to expected pages

----

- *Test:* Fill out various portions of the 'Feedback' section
- *Expected result:* The section should successfully submit the feedback and display a 'success' message and a button to return to the Dashboard
- ***Admin** expected result:* Verify that the feedback entry is stored in the `app_feedback` table

Go through each subsection, starting with the [Programs menu item](#programs-menu-item).

### Programs menu item
Select 'programs' on the menu. On the resulting page:

- *Test:* Verify all program information 
- *Expected result:* All program information is complete and accurate

----

- *Test:* Verify links work properly
- *Expected result:* All links are operational and lead to the correct pages

## Privacy Policy menu item
Select 'privacy policy' on the menu. On the resulting page:

- *Test:* Verify information is accurate
- *Expected result:* Privacy policy is complete and accurate and there is a button to return to the Dashboard

## Settings menu item
Select 'settings' on the menu. On the resulting page:

> Go through each link in 'settings' as many times as necessary to verify the changes you'd like to make

- Select the 'account' button
    - *Test:* Verify your information populate on the resulting 'step 1' page
    - *Expected result:* The information you previously submitted should be auto-populated in the form
    
    ----

    - *Test:* Change any information (noting the change) and select 'confirm'
    - *Expected result:* If you changed first or last name, the new name should be displayed on the 'settings' page. Select 'account' again and verify that all information that was changed is populated on the page
    - ***Admin** expected result:* Verify that the data changes are reflected in the `app_user` table

    - Select 'confirm' to return to the 'settings' page

- Select the 'address' button
    - *Test:* Verify your information populate on the 'step 2' page
    - *Expected result:* The information you previously submitted should be auto-populated in the form and the page should specify 'mailing address'
    
    ----

    - *Test:* Change the address - follow the same test cases in the [Where do you live](#step-2-where-do-you-live-page-address) section
        - Select 'confirm'
        - If the address confirmation displays, verify that the suggested address is correct and select the address
    - *Expected result:* From the 'settings' page, select 'address' again and verify that all information that was changed is populated on the page
    - ***Admin** expected result:* Verify that the data changes are reflected in the `app_address` table

    - Select 'confirm' to return to the 'settings' page

- Select the 'household' button
    - *Test:* Verify your household information is populated in the 'step 3' page
    - *Expected result:* The information you previously submitted should be auto-populated in the form
    
    ----

    - *Test:* Make a change to the household information and select 'confirm'
    - *Expected result:*
        - If the change was to the 'number of individuals', verify that the popup on the next page reflects a change and prompts you to verify your information
        - If no change was made to 'number of individuals', there should be no prompt and the [household member information](#step-3b-names-and-birthdates-of-household-members-household_members) page should be auto-populated with your previous inputs
        - Make any changes to the household member information and select 'confirm'
    - ***Admin** expected result:* Verify that the previous data have been stored in the `app_householdhist` table
    - ***Admin** expected result:* Verify that the data changes are reflected in the `app_household` table
        
    ----

    - *Test:* Select 'household' again to ensure the page populates with your changes
    - *Expected result:* Both pages for Step 3 should reflect the changes you made in the previous test