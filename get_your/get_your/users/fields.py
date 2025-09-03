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

from django.db.models import EmailField as EmailModelField
from django.forms import EmailField as EmailFormField

# class LowerEmailModelField(CaseInsensitiveFieldMixin, EmailModelField):
#     """Extend EmailModelField to be case-insensitive."""

#     def __init__(self, *args, **kwargs):
#         super(CaseInsensitiveFieldMixin, self).__init__(*args, **kwargs)


class LowercaseField:
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value:
            value = value.strip().lower()
        return value


class LowerEmailModelField(LowercaseField, EmailModelField):
    pass


class LowerEmailFormField(LowercaseField, EmailFormField):
    pass


# class LowerEmailModelField(EmailModelField, metaclass=models.SubfieldBase):
#     def __init__(self, *args, **kwargs):
#         self.is_lowercase = kwargs.pop("lowercase", False)
#         super(LowerEmailModelField, self).__init__(*args, **kwargs)

#     def get_prep_value(self, value):
#         value = super(LowerEmailModelField, self).get_prep_value(value)
#         if self.is_lowercase:
#             return value
#         return value.lower()

#     def to_python(self, value):
#         value = super().to_python(value)

#         # Value can be None so check that it's a string before lowercasing.
#         if isinstance(value, str):
#             return value.lower()

#         return value
