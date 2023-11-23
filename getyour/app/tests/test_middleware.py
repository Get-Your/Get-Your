from django.test import TestCase, Client
from django.shortcuts import reverse
from django.contrib.auth import login

from app import urls
from app.tests.user_init import TestUser

from app.backend import authenticate

class LoginRequiredTestCase(TestCase):
    """
    Test the LoginRequiredMiddleware.
    
    """


    def setUp(self):
        """ Set up the environment for testing. """

        # Every test needs access to the test client
        self.client = Client()

        # Every test needs access to a test user
        self.usermodel = TestUser()

    def test_logged_in_user(self):
        """
        Tests that logged-in users are passed directly to their target view.
        
        """

        # Gather all views in the 'app' namespace
        app_views = urls.urlpatterns

        for viewitm in app_views:
            with self.subTest(name=viewitm):

                # Login as self.usermodel user
                # user = authenticate(
                #     username=self.usermodel.user.email,
                #     password=self.usermodel.user.plaintext_password,
                # )
                self.client.login(
                    username=self.usermodel.user.email,
                    password=self.usermodel.user.plaintext_password,
                )

                # Test the view as if it were deployed to the user
                response = self.client.get(
                    reverse(f"app:{viewitm.name}"),
                    follow=True,
                    )
                
                self.assertURLEqual(
                    response.request['PATH_INFO'],
                    reverse(f"app:{viewitm.name}"),
                    )

                # self.assertRedirects(
                #     response,
                #     reverse(f"app:{viewitm.name}"),
                #     status_code=302,
                #     target_status_code=200,
                #     msg_prefix='',
                # )


    def tearDown(self):
        """ Remove the test user. """

        self.usermodel.destroy()
