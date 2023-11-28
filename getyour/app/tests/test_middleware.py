from django.test import TestCase, Client
from django.shortcuts import reverse
from django.http import HttpResponse

from app.tests.init_params import TestUser, TestView


def _get_target(
        class_instance,
        view_name: str,
        view_dict: dict,
        follow: bool = False,
    ) -> None:
    """
    Verify that the target is as expected.
    
    Parameters
    ----------
    class_instance
        ``self`` parameter from the calling class.
    view_name : str
        Name of the target view.
    view_dict : dict
        Dictionary of the target view, as defined by TestView.
    follow : bool, optional
        Specifies whether to follow the URL to the target or stop at first
        redirect (additional information at
        https://docs.djangoproject.com/en/4.1/topics/testing/tools/#django.test.Client
        ). The default is False, matching the django.test.Client default.

    Raises
    ------
    AssertionError
        Raises AssertionError if the target and actual URLs aren't equivalent.

    Returns
    -------
    HttpResponse
        Returns the response of the target

    """

    # Some pages require extra kwargs that must be included in 
    # reverse(); these must be a part of TestViews
    if 'kwargs' in view_dict:
        response = class_instance.client.get(
            reverse(
                f"app:{view_name}",
                kwargs=view_dict['kwargs'],
            ),
            follow=follow,
        )
    else:
        response = class_instance.client.get(
            reverse(f"app:{view_name}"),
            follow=follow,
        )

    return(response)


def _verify_successful_target(
        class_instance,
        response: HttpResponse,
        view_name: str,
        view_dict: dict,
    ) -> None:
    """
    Verify that the target is as expected.
    
    Parameters
    ----------
    class_instance
        ``self`` parameter from the calling class.
    response : HttpResponse
        Response from the test suite client.
    view_name : str
        Name of the target view.
    view_dict : dict
        Dictionary of the target view, as defined by TestView.

    Raises
    ------
    AssertionError
        Raises AssertionError if the target and actual URLs aren't equivalent.

    Returns
    -------
    None

    """

    # Some pages require extra kwargs that must be included in 
    # reverse(); these must be a part of TestViews
    if 'kwargs' in view_dict:
        class_instance.assertURLEqual(
            # Use .url if exists (for redirect)
            getattr(response, 'url', response.request['PATH_INFO']),
            reverse(
                f"app:{view_name}",
                kwargs=view_dict['kwargs'],
            ),
        )
    else:
        class_instance.assertURLEqual(
            # Use .url if exists (for redirect)
            getattr(response, 'url', response.request['PATH_INFO']),
            reverse(f"app:{view_name}"),
        )


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
                response = _get_target(
                    self,
                    viewname,
                    viewdict,
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
                    # Check for successful target
                    _verify_successful_target(
                        self,
                        response,
                        viewname,
                        viewdict,
                    )


    def tearDown(self):
        """ Remove the test user. """

        self.usermodel.destroy()
