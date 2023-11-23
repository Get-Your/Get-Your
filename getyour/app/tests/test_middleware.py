from django.test import TestCase, Client
from django.shortcuts import reverse
from django.urls.exceptions import NoReverseMatch

from app import urls
from app.tests.user_init import TestUser


class ValidRouteWhileLoggedIn(TestCase):
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
            with self.subTest(name=viewitm.name):

                # Login each time as self.usermodel user
                _ = self.client.login(
                    username=self.usermodel.user.email,
                    password=self.usermodel.user.plaintext_password,
                )

                # Try to go to that page
                try:
                    response = self.client.get(
                        reverse(f"app:{viewitm.name}"),
                        follow=True,
                    )

                # If the page can't be found with just the name, print and
                # continue
                except NoReverseMatch as e:
                    print(f"Error: {e}")

                else:
                    # If users aren't allowed direct access, HTTP 405 is expected
                    if viewitm.default_args['allow_direct_user']:
                        expected_status = 200
                    else:
                        expected_status = 405

                    self.assertEqual(
                        response.status_code,
                        expected_status,
                    )

                    # login is the only exception for target page being the
                    # same as source; it should send the user to /dashboard
                    if viewitm.name == 'login':
                        self.assertURLEqual(
                            response.request['PATH_INFO'],
                            reverse("app:dashboard"),
                        )

                    else:
                        self.assertURLEqual(
                            response.request['PATH_INFO'],
                            reverse(f"app:{viewitm.name}"),
                        )

    def tearDown(self):
        """ Remove the test user. """

        self.usermodel.destroy()
