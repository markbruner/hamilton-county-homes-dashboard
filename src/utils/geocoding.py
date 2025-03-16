import os
import re
import googlemaps
from config import zip_code_map

def is_only_city_state_country_regex(address):
    # Regex pattern to match strings that might include a country
    pattern = r'^\D+, \D+(, \D+)?$'
    return re.match(pattern, address) is not None

def address_has_no_street_number(address):
    # Regex pattern to match street names without a leading street number
    # This regex assumes that the street number, if present, would typically appear at the start
    pattern = r'^[^\d]+\b\w*(?:[a-z]{2,10})\b'

    return re.match(pattern, address) is not None

def get_address_details_with_cities(address,school_district):
    # Initialize the Google Maps client with your API key
    api_key = os.getenv("MAPS_API_KEY")
    gmaps = googlemaps.Client(key=api_key)

    for zip_code in zip_code_map[school_district]:
        full_address_query = f"{address} {zip_code}"
        # Make the geocoding request
        try:
            response = gmaps.geocode(full_address_query)
        except Exception as e:
            print(f"Geocoding failed for {full_address_query}: {e}")
            continue
        # Filtering the results for only ROOFTOP location types
        rooftop_results = [result for result in response if result['geometry']['location_type'] == 'ROOFTOP']
        if rooftop_results:
            result = rooftop_results[0] 
            formatted_address = result['formatted_address']
            location = result['geometry']['location']
        # # Check if the formatted address is not just city, state, country
            return {
                'formatted_address': formatted_address,
                'longitude': location['lng'],
                'latitude': location['lat']
            }    
        # Return if no rooftop result found for the current zip code
        # print(f"{full_address_query}: No ROOFTOP result found.")
        
    # If no valid address is found after all attempts
    print(full_address_query, "No valid address found.")
    return {'formatted_address': None, 'longitude': None, 'latitude': None}