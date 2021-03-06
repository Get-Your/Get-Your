# Grace User Authentication
from django.contrib.auth.backends import ModelBackend, UserModel
from django.contrib.auth import get_user_model

from django.contrib.auth.hashers import check_password

def authenticate(username=None, password=None):
    User = get_user_model()
    try: #to allow authentication through phone number or any other field, modify the below statement
        user = User.objects.get(email=username)
        print(user)
        print(password)
        print(user.password)
        print(user.check_password(password))
        if user.check_password(password):
            return user 
        return None
    except User.DoesNotExist:
        return None

def get_user(self, user_id):
    try:
        return UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return None

def files_to_string(file_list):
    list_string = ""
    counter = 0

    # Get File_List into easy to read list to print out in template
    for key, value in file_list.items():
        # only add things to the list_string if its true
        if value == True:
            # Also add commas based on counter
            if counter == 1:
                list_string += ", "
                counter = 0
            else:
                counter = 1
            list_string += key
    return list_string