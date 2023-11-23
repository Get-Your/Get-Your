from django.test import TestCase

from app import urls
from app.tests.init_params import TestView


class URLconfViewsAccountedFor(TestCase):
    """
    Test whether all URLconf views are accounted for in TestView.
    
    """

    def setUp(self):
        """ Set up the environment for testing. """
        
        # Gather views from initialization script
        self.testviews = TestView()

        # Gather all none-None views in the 'app' namespace
        self.app_views = [x.name for x in urls.urlpatterns if x.name is not None]

    def test_urlconf_views(self):
        """
        Tests that the view names in URLconf are also specified in TestView.
        
        """

        # Loop through app_views as the source of truth
        for viewname in self.app_views:
            with self.subTest(expected_view=viewname):

                # Assert that a testviews element of the same name exists
                self.assertTrue(
                    viewname in self.testviews.named_app_views.keys()
                )


class TestViewViewsAccountedFor(TestCase):
    """
    Test whether all TestViews are also in URLconf.
    
    """

    def setUp(self):
        """ Set up the environment for testing. """
        
        # Gather views from view_init
        self.testviews = TestView()

        # Gather all none-None views in the 'app' namespace
        self.app_views = [x.name for x in urls.urlpatterns if x.name is not None]

    def test_testview_views(self):
        """
        Tests that the view names in TestView are also specified in URLconf.
        
        """

        # Loop through TestView as the source of truth
        for viewname in self.testviews.named_app_views.keys():
            with self.subTest(test_view=viewname):

                # Assert that a URLconf element of the same name exists
                self.assertTrue(
                    viewname in self.app_views
                )


class TestViewsHaveRequiredKeys(TestCase):
    """
    Test whether all views in TestView have the required dict keys.
    
    """

    def setUp(self):
        """ Set up the environment for testing. """
        
        # Gather views from view_init
        self.testviews = TestView()

    def test_all_views(self):
        """
        Tests that all required keys exist in the views to test.
        
        """

        # Loop through each key in named_app_views
        for viewname in self.testviews.named_app_views.keys():
            with self.subTest(name=viewname):

                # Ensure all necessary keys are in the test dict
                for keyval in self.testviews.required_keys:
                    self.assertTrue(
                        keyval in self.testviews.named_app_views[viewname]
                    )
