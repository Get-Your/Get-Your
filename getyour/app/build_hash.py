"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2023

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

import hashlib

def hash_address(address_dict: dict) -> str:
    """ 
    Create a SHA-1 hash from existing address values.
    :param address_dict: Dictionary of user-entered address fields.
    :returns str: String representation of SHA-1 address hash. SHA-1 hash is
        160 bits; written as hex for 40 characters.
    """
    # Explicitly define address field order
    keyList = ['address1', 'address2', 'city', 'state', 'zip_code']
    # Concatenate string representations of each value in sequence.
    # If value is string, convert to uppercase; if key DNE, use blank string.
    concatVals = ''.join(
        [address_dict[key].upper() if key in address_dict.keys() and isinstance(address_dict[key], str) \
         else str(address_dict[key]) if key in address_dict.keys() \
            else '' for key in keyList]
            )
    # Return SHA-1 hash of the concatenated strings
    return hashlib.sha1(bytearray(concatVals, 'utf8')).hexdigest()