from django.test import TestCase, Client
from django.shortcuts import reverse

from app.tests.init_params import TestUser, TestView


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

        # Every test needs access to the views to test
        self.testviews = TestView()

    def test_logged_in_user(self):
        """
        Tests that logged-in users are passed directly to their target view.
        
        """

        for viewname, viewdict in self.testviews.named_app_views.items():
            with self.subTest(name=viewname):

                # Login each time as self.usermodel user
                _ = self.client.login(
                    username=self.usermodel.user.email,
                    password=self.usermodel.user.plaintext_password,
                )

                # Try to go to that page

                # Some pages require extra kwargs that must be included in 
                # reverse(); these must be a part of TestViews
                if 'kwargs' in viewdict:
                    response = self.client.get(
                        reverse(
                            f"app:{viewname}",
                            kwargs=viewdict['kwargs'],
                        ),
                        follow=True,
                    )
                else:
                    response = self.client.get(
                        reverse(f"app:{viewname}"),
                        follow=True,
                    )

                # If users aren't allowed direct access, HTTP 405 is expected
                if viewdict['direct_access_allowed']:
                    expected_status = 200
                else:
                    expected_status = 405

                self.assertEqual(
                    response.status_code,
                    expected_status,
                )

                # login is the only exception for target page being the
                # same as source; it should send the user to /dashboard
                if viewname == 'login':
                    self.assertURLEqual(
                        response.request['PATH_INFO'],
                        reverse("app:dashboard"),
                    )

                else:
                    # Some pages require extra kwargs that must be included in 
                    # reverse(); these must be a part of TestViews
                    if 'kwargs' in viewdict:
                        self.assertURLEqual(
                            response.request['PATH_INFO'],
                            reverse(
                                f"app:{viewname}",
                                kwargs=viewdict['kwargs'],
                            ),
                        )
                    else:
                        self.assertURLEqual(
                            response.request['PATH_INFO'],
                            reverse(f"app:{viewname}"),
                        )


    def tearDown(self):
        """ Remove the test user. """

        self.usermodel.destroy()
