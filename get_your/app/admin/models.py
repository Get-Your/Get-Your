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

from enum import Flag


class PermissionDefinitions:
    """
    Enumeration of the available staff permissions. These are defined
    approximately hierarchically, where each subsequent value has fewer overall
    permissions. StaffPermissions, below, provides lookups and helper functions
    to determine the exact permission for a particular use case.

    Only permissions defined here will be available for parsing when rendering
    the admin site.

    """

    def __init__(self):
        # Define the permissions name and it's group mapping, if it has one
        self._mapping = {
            "SUPERUSER": {
                "order": 1,
                # Special case: defined by built-in `is_superuser` User attribute
                "group": None,
            },
            "PROGRAM_ADMIN": {
                "order": 2,
                # Defined by membership in 'admin_program' auth group
                "group": "admin_program",
            },
            "INCOME_VERIFICATION": {
                "order": 3,
                # Defined by membership in 'income_verification_staff' auth group
                "group": "income_verification_staff",
            },
        }

        # Use Flag to allow Boolean comparisons in StaffPermissions.contains()
        self.groups = Flag(
            "Permissions Groups",
            # List the permissions group names, using 'order' for placement
            [
                x[0]
                for x in sorted(
                    self._mapping.items(),
                    key=lambda itm: itm[1]["order"],
                )
            ],
        )


class StaffPermissions:
    """Define a [non-database] model to parse and store staff permissions."""

    def __init__(self, user):
        permission_definitions = PermissionDefinitions()
        self._available_groups = permission_definitions.groups

        # Initialize the helper vars
        self.__highest = None
        self.__groups = ()

        # Use the user object to get the auth group memberships, if applicable,
        # and define the appropriate helper vars. Note that these are in order
        # of `_available_groups` (for the append functions)
        if user.is_staff:
            for grp in self._available_groups:
                # Initialize is_member to False
                is_member = False
                auth_group = permission_definitions._mapping[grp.name]["group"]

                if auth_group is None:
                    # Special case for 'SUPERUSER'
                    if (
                        grp == permission_definitions.groups.SUPERUSER
                        and user.is_superuser
                    ):
                        is_member = True
                elif user.groups.filter(name=auth_group).exists():
                    is_member = True

                # Process the helper vars
                if is_member:
                    # Append the group to `groups`
                    self.add_groups(grp)
                    # Set `highest` the first time it's not None (since this
                    # loops in hierarchical order)
                    if not self.__highest:
                        self.__highest = grp

    def add_groups(self, *args):
        # Add all args to 'groups'
        self.__groups = tuple(list(self.__groups) + list(args))

    def contains(self, *args):
        # Use each value in args to search.
        # Note that this can be improved with the enum API in Python >3.11
        # (https://docs.python.org/3.11/library/enum.html#enum.Flag), by setting
        # self.__groups as a slice of permission_definitions.groups then using
        # the __contains__() built-in
        for itm in args:
            # Use truthiness of ANDed Flag to search for itm in self.__groups
            has_member = next(
                (True for x in self.__groups if x & itm),
                False,
            )

            # Break and return the first time has_member is True
            if has_member:
                break

        return has_member

    @property
    def highest(self):
        """
        Define the "highest" permissions level.

        Note that this is effectively read-only because no @setter is defined.

        """
        return self.__highest

    @property
    def groups(self):
        """
        Define the permissions groups the user is part of.

        Note that this is effectively read-only because no @setter is defined.

        """
        return self.__groups
