"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import re
from inspect import getmembers

from django.db.models.query_utils import DeferredAttribute
from django.test import TestCase

from ref.models import Address as AddressRef
from ref.models import IQProgram as IQProgramRef


class RequiresFieldsHaveCorrespondingAddressField(TestCase):
    """
    Test whether all 'requires_' fields in IQProgramRef have a corresponding
    field in AddressRef. These fields are expected to be in the format
    `<address field name>` and `requires_<address field name>`.

    """

    def setUp(self):
        """Set up the environment for testing."""

        def is_data_field(obj):
            """
            Determine if the input object is a model field, using a test found
            in django.contrib.auth.apps in Django v4.1.

            """
            return isinstance(obj, DeferredAttribute)

        # Gather all user-defined fields in the IQProgramRef model
        IQProgramRef_fields = [x[0] for x in getmembers(IQProgramRef, is_data_field)]

        # Use all 'requires_' fields for this test, but let's try to
        # Murphy-proof a bit - search instead for fields that start with 'req'
        self.requires_fields = [x for x in IQProgramRef_fields if x.startswith("req")]

        # Gather all user-defined fields in the AddressRef model
        self.address_fields = [x[0] for x in getmembers(AddressRef, is_data_field)]

    def test_corresponding_fields(self):
        """
        Tests that each elements of self.requires_fields has a corresponding
        field in AddressRef (following the naming convention described in the
        class docstring).

        """

        # Loop through requires_fields
        for fd in self.requires_fields:
            with self.subTest(expected_view=fd):
                # Assert that a corresponding field with the expected name exists

                # Use regexp to continue with the search of just 'req' instead
                # of 'requires_'
                expected_corresponding_field = re.sub(r"^req\w*?_", "", fd)

                # Confirm that the field exists in AddressRef
                self.assertTrue(
                    expected_corresponding_field in self.address_fields,
                )
