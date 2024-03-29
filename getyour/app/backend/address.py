"""
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2022-2024

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

from usps import USPSApi, Address

from django import http
from django.conf import settings

from logger.wrappers import LoggerWrapper

# Initialize logger
log = LoggerWrapper(logging.getLogger(__name__))


# Use the following tag mapping for USPS standards for all functions
tag_mapping = {
    'Recipient': 'recipient',
    'AddressNumber': 'address_2',
    'AddressNumberPrefix': 'address_2',
    'AddressNumberSuffix': 'address_2',
    'StreetName': 'address_2',
    'StreetNamePreDirectional': 'address_2',
    'StreetNamePreModifier': 'address_2',
    'StreetNamePreType': 'address_2',
    'StreetNamePostDirectional': 'address_2',
    'StreetNamePostModifier': 'address_2',
    'StreetNamePostType': 'address_2',
    'CornerOf': 'address_2',
    'IntersectionSeparator': 'address_2',
    'LandmarkName': 'address_2',
    'USPSBoxGroupID': 'address_2',
    'USPSBoxGroupType': 'address_2',
    'USPSBoxID': 'address_2',
    'USPSBoxType': 'address_2',
    'BuildingName': 'address_1',
    'OccupancyType': 'address_1',
    'OccupancyIdentifier': 'address_1',
    'SubaddressIdentifier': 'address_1',
    'SubaddressType': 'address_1',
    'PlaceName': 'city',
    'StateName': 'state',
    'ZipCode': 'zipcode',
}


def address_check(address_dict):
    """
    Check for address GMA and Connexion statuses.

    Parameters
    ----------
    instance : dict
        Post-USPS-validation dictionary. Usable data for this script are in
        ['AddressValidateResponse']['Address'][...].

    Returns
    -------
    bool
        Whether the address is in the GMA (True, False).
    bool
        The status of Connexion service (True, False, None).

    """

    try:
        # Gather the coordinate string for future queries
        # Parse the 'instance' data for proper 'address_parts'
        address_parts = "{}, {}".format(
            address_dict['AddressValidateResponse']['Address']['Address2'],
            address_dict['AddressValidateResponse']['Address']['Zip5'],
        )
        coord_string = address_lookup(address_parts)

    except NameError:
        # NameError specifies that the address is not found
        # in City lookups and is therefore *probably* not in the IQ
        # service area

        # Log a potential error if the city is 'Fort Collins'
        if address_dict['AddressValidateResponse']['Address']['City'].lower() == 'fort collins':    
            log.error(
                "Potential issue: Fort Collins address marked 'not in GMA': {}".format(
                    address_dict['AddressValidateResponse']['Address'],
                ),
                function='address_check',
            )

        return (False, False)

    else:
        has_connexion = connexion_lookup(coord_string)
        msg = 'Connexion not available or API not found' if has_connexion is None \
            else 'Connexion available' if has_connexion \
            else 'Connexion coming soon'
        log.info(msg, function='address_check')

        is_in_gma = gma_lookup(coord_string)
        msg = 'Address is in GMA' if is_in_gma else 'Address is outside of GMA'
        log.info(msg, function='address_check')

        return (is_in_gma, has_connexion)


def address_lookup(address_parts):
    """
    Look up the coordinates for an address to input into future queries.

    Parameters
    ----------
    address_parts : str
        The address parts to use for the lookup (specifically in the format
        <address_2>, <zip code>) (e.g. "300 LAPORTE AVE, 80521", sans quotes).

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

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/Geocode/Fort_Collins_Area_Address_Point_Geocoding_Service/GeocodeServer/findAddressCandidates'

    payload = {
        'f': 'pjson',
        'Street': address_parts,
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

    # Since the gisweb endpoint seems to always return an HTTP 200, also check
    # the JSON for an 'error' key
    if 'error' in outVal:
        errDict = outVal['error']
        log.error(
            f"API error {errDict['code']}: {errDict['message']}",
            function='address_lookup',
        )
        raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

    # Ensure candidate(s) exist and they have a decent match score
    # Because this is how the Sales Tax lookup is architected, it should be
    # safe to assume these are returned sorted, with best candidate first
    if len(outVal['candidates']) > 0 and outVal['candidates'][0]['score'] > 85:
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

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/FDH_Boundaries_ForPublic/MapServer/0/query'

    payload = {
        'f': 'pjson',
        'geometryType': 'esriGeometryPoint',
        'geometry': coord_string,
    }

    try:
        # Gather response
        response = requests.post(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function='connexion_lookup',
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if 'error' in outVal:
            errDict = outVal['error']
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function='connexion_lookup',
            )
            raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

        statusInput = outVal['features'][0]['attributes']['INVENTORY_STATUS_CODE']

    except requests.exceptions.HTTPError:
        return None

    except (IndexError, KeyError):
        return None

    else:
        statusInput = statusInput.lower()

        # If we made it to this point, Connexion will be or is currently
        # available
        if statusInput in (
                'released',
                'out of warranty',
        ):      # this is the 'available' case
            return True

        else:
            return False


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

    url = 'https://gisweb.fcgov.com/arcgis/rest/services/FCMaps/MapServer/26/query'

    payload = {
        # Manually stringify 'geometry' - requests and json.dumps do this
        # incorrectly
        'geometry': """{"points":[["""+coord_string+"""]],"spatialReference":{"wkid":102653}}""",
        'geometryType': 'esriGeometryMultipoint',
        'inSR': 2231,
        'spatialRel': 'esriSpatialRelIntersects',
        'where': '',
        'returnGeometry': 'false',
        'outSR': 2231,
        'outFields': '*',
        'f': 'pjson',
    }

    try:
        # Gather response
        response = requests.get(url, params=payload)
        if response.status_code != requests.codes.ok:
            log.error(
                f"API error {response.status_code}: {response.reason}; {response.content}",
                function='gma_lookup',
            )
            raise requests.exceptions.HTTPError(response.reason, response.content)

        # Parse response
        outVal = response.json()

        # Since the gisweb endpoint seems to always return an HTTP 200, also check
        # the JSON for an 'error' key
        if 'error' in outVal:
            errDict = outVal['error']
            log.error(
                f"API error {errDict['code']}: {errDict['message']}",
                function='gma_lookup',
            )
            raise requests.exceptions.HTTPError(errDict['code'], errDict['message'])

        if len(outVal['features']) > 0:
            return True
        else:
            return False

    except requests.exceptions.HTTPError:
        return False


def validate_usps(inobj):
    if isinstance(inobj, http.request.QueryDict):
        # Combine fields into Address
        address = Address(
            name=" ",
            address_1=inobj['address'],
            address_2=inobj['address2'],
            city=inobj['city'],
            state=inobj['state'],
            zipcode=inobj['zipcode'],
        )

    elif isinstance(inobj, dict):
        address = Address(**inobj)

    else:
        raise AttributeError('Unknown validation input')

    usps = USPSApi(settings.USPS_SID, test=True)
    validation = usps.validate_address(address)
    outDict = validation.result
    try:
        log.info(
            f"Address dict found: {outDict}",
            function='validate_usps',
        )
        return outDict

    except KeyError:
        log.exception(
            "Address could not be found - no guesses",
            function='validate_usps',
        )
        raise
