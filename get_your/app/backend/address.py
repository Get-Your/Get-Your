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

import logging
import requests

from django import http
from django.conf import settings
from django.contrib.auth import get_user_model
from monitor.wrappers import LoggerWrapper
from urllib.parse import quote, urlencode

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))

# Get the user model
User = get_user_model()

# Use the following tag mapping for USPS standards for all functions
tag_mapping = {
    'Recipient': 'recipient',
    'AddressNumber': 'streetAddress',
    'AddressNumberPrefix': 'streetAddress',
    'AddressNumberSuffix': 'streetAddress',
    'StreetName': 'streetAddress',
    'StreetNamePreDirectional': 'streetAddress',
    'StreetNamePreModifier': 'streetAddress',
    'StreetNamePreType': 'streetAddress',
    'StreetNamePostDirectional': 'streetAddress',
    'StreetNamePostModifier': 'streetAddress',
    'StreetNamePostType': 'streetAddress',
    'CornerOf': 'streetAddress',
    'IntersectionSeparator': 'streetAddress',
    'LandmarkName': 'streetAddress',
    'USPSBoxGroupID': 'streetAddress',
    'USPSBoxGroupType': 'streetAddress',
    'USPSBoxID': 'streetAddress',
    'USPSBoxType': 'streetAddress',
    'BuildingName': 'secondaryAddress',
    'OccupancyType': 'secondaryAddress',
    'OccupancyIdentifier': 'secondaryAddress',
    'SubaddressIdentifier': 'secondaryAddress',
    'SubaddressType': 'secondaryAddress',
    'PlaceName': 'city',
    'StateName': 'state',
    'ZipCode': 'ZIPCode',
}


def address_check(address_dict):
    """
    Check for address GMA and Connexion statuses.

    Parameters
    ----------
    instance : dict
        Post-USPS-validation dictionary.

    Returns
    -------
    bool
        Whether the address is in the GMA (True, False).
    bool
        The status of Connexion service (True, False, None).

    """

    try:
        # Gather the coordinate string for future queries
        coord_string = address_lookup(
            address_dict['streetAddress'],
            address_dict['ZIPCode'],
        )

    except NameError:
        # NameError specifies that the address is not found
        # in City lookups and is therefore *probably* not in the IQ
        # service area

        # Log a potential error if the city is 'Fort Collins'
        if address_dict['city'].lower() == 'fort collins':
            log.error(
                "Potential issue: Fort Collins address marked 'not in GMA': {}".format(
                    address_dict,
                ),
                function="address_check",
            )

        return (False, False)

    else:
        has_connexion = connexion_lookup(coord_string)
        msg = (
            "Connexion not available or API not found"
            if has_connexion is None
            else "Connexion available"
            if has_connexion
            else "Connexion coming soon"
        )
        log.info(msg, function="address_check")

        is_in_gma = gma_lookup(coord_string)
        msg = "Address is in GMA" if is_in_gma else "Address is outside of GMA"
        log.info(msg, function="address_check")

        return (is_in_gma, has_connexion)


def address_lookup(street_address, zip_code):
    """
    Look up the coordinates for an address to input into future queries.

    Parameters
    ----------
    street_address : str
        The 'street address' (line 1 of the address) to use for the lookup.
    zip_code : str
        The 5-digit ZIP code (as a string, from the USPS API) to use for the
        lookup.

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.
    NameError
        Address not found in City lookups - address is not in IQ service area.

    Returns
    -------
    str
        Formatted string of x,y coordinates for the address, to input in
        future queries.

    """

    # API documentation at
    # https://developers.arcgis.com/rest/geocode/find-address-candidates
    url = 'https://gis.fortcollins.gov/arcgis/rest/services/Geocode/Fort_CollinsAddress_Point_Locator_Pro_New_/GeocodeServer/findAddressCandidates'

    # While there are many more options than the prior endpoint, it seems the
    # best results are garnered with the minimum input
    payload = {
        'f': 'pjson',
        'address': street_address,
        'postal': zip_code,
        'outFields': 'location',
    }

    # Gather response
    response = requests.get(url, params=payload)
    if response.status_code != requests.codes.ok:
        log.error(
            f"API error {response.status_code}: {response.reason}; {response.content}",
            function='address_lookup',
        )
        raise requests.exceptions.HTTPError(response.reason, response.content)

    # Parse response
    outVal = response.json()

    # An HTTP 200 still could have an error output; check the JSON for an
    # 'error' key
    if 'error' in outVal:
        errDict = outVal['error']
        log.error(
            f"API error {errDict['code']}: {errDict['message']}",
            function='address_lookup',
        )
        # TODO: Allow this error message to populate a custom HTTP error page
        # that has select messages for the user (e.g. this one could be
        # something like "There was an error and your application can't be
        # completed right now. Your information has been saved; please try again
        # later")
        raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

    # Ensure candidate(s) exist and they have a decent match score
    # The endpoint has smart matching and even exact inputs result in fairly
    # low scores; set the 'minimum score' somewhat low to avoid missing accurate
    # matches

    # Because this is how the Sales Tax lookup is architected, it should be
    # safe to assume these are returned sorted, with best candidate first
    if len(outVal['candidates']) > 0 and outVal['candidates'][0]['score'] > 69.9:
        # Define the coordinate string to be used in future queries
        coord_string = '{x},{y}'.format(
            x=outVal['candidates'][0]['location']['x'],
            y=outVal['candidates'][0]['location']['y'],
        )

    else:
        raise NameError("Matching address not found")

    return coord_string


def connexion_lookup(coord_string):
    """
    Look up the Connexion service status given the coordinate string.

    Parameters
    ----------
    coord_string : str
        Formatted <x>,<y> string of coordinates from address_lookup().

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.
    IndexError
        Address not found in Connexion lookups - Connexion is likely to be
        unavailable at this address.

    Returns
    -------
    bool
        Boolean 'status', designating True for 'service available' or False
        for 'service will be available, but not yet' OR None for 'unavailable'
        (probably)

    TODO: Switch this to an enum if we want to keep this structure

    """

    url = "https://gisweb.fcgov.com/arcgis/rest/services/FDH_Boundaries_ForPublic/MapServer/0/query"

    payload = {
        "f": "pjson",
        "geometryType": "esriGeometryPoint",
        "geometry": coord_string,
    }

    try:
        # Gather response
        response = requests.post(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function="connexion_lookup",
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if "error" in outVal:
            errDict = outVal["error"]
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function="connexion_lookup",
            )
            raise requests.exceptions.HTTPError(errDict["code"], errDict["message"])

        statusInput = outVal["features"][0]["attributes"]["INVENTORY_STATUS_CODE"]

    except requests.exceptions.HTTPError:
        return None

    except (IndexError, KeyError):
        return None

    else:
        statusInput = statusInput.lower()

        # If we made it to this point, Connexion will be or is currently
        # available
        return statusInput in ("released", "out of warranty")


def gma_lookup(coord_string):
    """
    Look up the GMA location given the coordinate string.

    Parameters
    ----------
    coord_string : str
        Formatted <x>,<y> string of coordinates from address_lookup().

    Raises
    ------
    requests.exceptions.HTTPError
        An issue with the lookup endpoint.

    Returns
    -------
    Boolean 'status', designating True for an address within the GMA, or False
    otherwise.

    """

    url = "https://gisweb.fcgov.com/arcgis/rest/services/FCMaps/MapServer/26/query"

    payload = {
        # Manually stringify 'geometry' - requests and json.dumps do this
        # incorrectly
        "geometry": """{"points":[["""
        + coord_string
        + """]],"spatialReference":{"wkid":102653}}""",
        "geometryType": "esriGeometryMultipoint",
        "inSR": 2231,
        "spatialRel": "esriSpatialRelIntersects",
        "where": "",
        "returnGeometry": "false",
        "outSR": 2231,
        "outFields": "*",
        "f": "pjson",
    }

    try:
        # Gather response
        response = requests.get(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function="gma_lookup",
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if "error" in outVal:
            errDict = outVal["error"]
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function="gma_lookup",
            )
            raise requests.exceptions.HTTPError(errDict["code"], errDict["message"])

        if len(outVal["features"]) > 0:
            return True
        return False

    except requests.exceptions.HTTPError:
        return False


def get_usps_token():
    """Get the bearer token for the USPS v3 API."""

    # Gather the token with the 'addresses' scope
    response = requests.post(
        'https://apis.usps.com/oauth2/v3/token',
        data={
            'grant_type': 'client_credentials',
            'scope': 'addresses',
            'client_id': settings.USPS_KEY,
            'client_secret': settings.USPS_SECRET,
        },
        timeout=10,
    )

    response_dict = response.json()
    if not response.ok or 'access_token' not in response_dict:
        log.exception(
            response.text,
            function='get_usps_token',
        )
        response.raise_for_status()
    return response_dict['access_token']


def validate_usps(inobj):
    if isinstance(inobj, http.request.QueryDict):
        # Define the mapper of inobj keys to arguments used in the USPS v3 API
        key_map = {
            'address1': 'streetAddress',
            'address2': 'secondaryAddress',
            'city': 'city',
            'state': 'state',
            'zipcode': 'ZIPCode',
        }
        # Create address, using only non-blank values
        address = {key_map[key]: val for key, val in inobj.items() if val!=''}

    elif isinstance(inobj, dict):
        # Create address, using only non-blank values
        address = {key: val for key, val in inobj.items() if val!=''}

    else:
        raise AttributeError('Unknown validation input')

    # Ensure 'state' is uppercase (otherwise the API will error)
    address['state'] = address['state'].upper()

    # TODO: Update this to use an existing token, if still valid (rather than
    # calling this each time)
    access_token = get_usps_token()

    # Call the USPS 'addresses' API with the parsed input. urljoin(),
    # urlencode(), and quote are used so that spaces are escaped with '%20'
    # instead of '+' (as requests-native functionality does)
    response = requests.get(
        "https://apis.usps.com/addresses/v3/address?{}".format(
            urlencode(
                address,
                quote_via=quote,
            ),
        ),
        timeout=10,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )

    # Log then raise an error and raise if status_code != 200
    if not response.ok:
        log.exception(
            f"Address could not be found; error {response.text}",
            function='validate_usps',
        )
        response.raise_for_status()

    # Log and return the dictionary
    response_dict = response.json()
    log.info(
        f"Address dict found: {response_dict}",
        function='validate_usps',
    )
    return response_dict


def finalize_address(instance, is_in_gma, has_connexion):
    """
    Finalize the address, given inputs calculated earlier in the application.

    """

    # Record the service area and Connexion status
    instance.is_in_gma = is_in_gma
    instance.is_city_covered = is_in_gma
    instance.has_connexion = has_connexion

    # Final step: mark the address record as 'verified' and save
    instance.is_verified = True
    instance.save()
