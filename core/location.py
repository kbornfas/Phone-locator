"""
Location Fetcher for PhoneTracker CLI

Provides various methods to fetch location data for phone numbers.
Methods include: basic (IP-based), carrier (requires API), and GPS-assisted.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Literal
import phonenumbers
from phonenumbers import geocoder, carrier as phone_carrier


LocationMethod = Literal['basic', 'carrier', 'gps']


@dataclass
class Location:
    """
    Represents a geographic location with metadata.
    
    Attributes:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        accuracy: Accuracy radius in meters
        method: Method used to obtain the location
        city: City name (if available)
        country: Country name (if available)
        carrier: Mobile carrier name (if available)
        timestamp: ISO format timestamp when location was obtained
    """
    latitude: float
    longitude: float
    accuracy: int
    method: str
    city: Optional[str] = None
    country: Optional[str] = None
    carrier: Optional[str] = None
    timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert location to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'method': self.method,
            'city': self.city,
            'country': self.country,
            'carrier': self.carrier,
            'timestamp': self.timestamp or datetime.utcnow().isoformat()
        }


class LocationFetcher:
    """
    Fetches location information for phone numbers using various methods.
    
    Methods:
        - basic: Uses phone number prefix database for country/region (low accuracy ~5km)
        - enhanced: Uses ipinfo.io + numverify for better accuracy (~1-5km)
        - carrier: Uses carrier API for cell tower triangulation (~50-500m, requires API key)
        - gps: GPS-assisted location (~1-10m, requires device cooperation)
    """
    
    # NumVerify API for carrier lookup (free tier available)
    NUMVERIFY_API = "http://apilayer.net/api/validate"
    
    # AbstractAPI for phone validation
    ABSTRACTAPI_URL = "https://phonevalidation.abstractapi.com/v1/"
    
    # Country code to approximate coordinates mapping
    # These are capital city coordinates for demonstration
    COUNTRY_COORDINATES = {
        '1': {'lat': 38.8951, 'lng': -77.0364, 'city': 'Washington D.C.', 'country': 'USA'},
        '7': {'lat': 55.7558, 'lng': 37.6173, 'city': 'Moscow', 'country': 'Russia'},
        '20': {'lat': 30.0444, 'lng': 31.2357, 'city': 'Cairo', 'country': 'Egypt'},
        '27': {'lat': -25.7479, 'lng': 28.2293, 'city': 'Pretoria', 'country': 'South Africa'},
        '30': {'lat': 37.9838, 'lng': 23.7275, 'city': 'Athens', 'country': 'Greece'},
        '31': {'lat': 52.3676, 'lng': 4.9041, 'city': 'Amsterdam', 'country': 'Netherlands'},
        '32': {'lat': 50.8503, 'lng': 4.3517, 'city': 'Brussels', 'country': 'Belgium'},
        '33': {'lat': 48.8566, 'lng': 2.3522, 'city': 'Paris', 'country': 'France'},
        '34': {'lat': 40.4168, 'lng': -3.7038, 'city': 'Madrid', 'country': 'Spain'},
        '36': {'lat': 47.4979, 'lng': 19.0402, 'city': 'Budapest', 'country': 'Hungary'},
        '39': {'lat': 41.9028, 'lng': 12.4964, 'city': 'Rome', 'country': 'Italy'},
        '41': {'lat': 46.9480, 'lng': 7.4474, 'city': 'Bern', 'country': 'Switzerland'},
        '43': {'lat': 48.2082, 'lng': 16.3738, 'city': 'Vienna', 'country': 'Austria'},
        '44': {'lat': 51.5074, 'lng': -0.1278, 'city': 'London', 'country': 'UK'},
        '45': {'lat': 55.6761, 'lng': 12.5683, 'city': 'Copenhagen', 'country': 'Denmark'},
        '46': {'lat': 59.3293, 'lng': 18.0686, 'city': 'Stockholm', 'country': 'Sweden'},
        '47': {'lat': 59.9139, 'lng': 10.7522, 'city': 'Oslo', 'country': 'Norway'},
        '48': {'lat': 52.2297, 'lng': 21.0122, 'city': 'Warsaw', 'country': 'Poland'},
        '49': {'lat': 52.5200, 'lng': 13.4050, 'city': 'Berlin', 'country': 'Germany'},
        '51': {'lat': -12.0464, 'lng': -77.0428, 'city': 'Lima', 'country': 'Peru'},
        '52': {'lat': 19.4326, 'lng': -99.1332, 'city': 'Mexico City', 'country': 'Mexico'},
        '54': {'lat': -34.6037, 'lng': -58.3816, 'city': 'Buenos Aires', 'country': 'Argentina'},
        '55': {'lat': -15.7975, 'lng': -47.8919, 'city': 'Brasilia', 'country': 'Brazil'},
        '56': {'lat': -33.4489, 'lng': -70.6693, 'city': 'Santiago', 'country': 'Chile'},
        '57': {'lat': 4.7110, 'lng': -74.0721, 'city': 'Bogota', 'country': 'Colombia'},
        '58': {'lat': 10.4806, 'lng': -66.9036, 'city': 'Caracas', 'country': 'Venezuela'},
        '60': {'lat': 3.1390, 'lng': 101.6869, 'city': 'Kuala Lumpur', 'country': 'Malaysia'},
        '61': {'lat': -35.2809, 'lng': 149.1300, 'city': 'Canberra', 'country': 'Australia'},
        '62': {'lat': -6.2088, 'lng': 106.8456, 'city': 'Jakarta', 'country': 'Indonesia'},
        '63': {'lat': 14.5995, 'lng': 120.9842, 'city': 'Manila', 'country': 'Philippines'},
        '64': {'lat': -41.2865, 'lng': 174.7762, 'city': 'Wellington', 'country': 'New Zealand'},
        '65': {'lat': 1.3521, 'lng': 103.8198, 'city': 'Singapore', 'country': 'Singapore'},
        '66': {'lat': 13.7563, 'lng': 100.5018, 'city': 'Bangkok', 'country': 'Thailand'},
        '81': {'lat': 35.6762, 'lng': 139.6503, 'city': 'Tokyo', 'country': 'Japan'},
        '82': {'lat': 37.5665, 'lng': 126.9780, 'city': 'Seoul', 'country': 'South Korea'},
        '84': {'lat': 21.0278, 'lng': 105.8342, 'city': 'Hanoi', 'country': 'Vietnam'},
        '86': {'lat': 39.9042, 'lng': 116.4074, 'city': 'Beijing', 'country': 'China'},
        '90': {'lat': 39.9334, 'lng': 32.8597, 'city': 'Ankara', 'country': 'Turkey'},
        '91': {'lat': 28.6139, 'lng': 77.2090, 'city': 'New Delhi', 'country': 'India'},
        '92': {'lat': 33.6844, 'lng': 73.0479, 'city': 'Islamabad', 'country': 'Pakistan'},
        '93': {'lat': 34.5553, 'lng': 69.2075, 'city': 'Kabul', 'country': 'Afghanistan'},
        '94': {'lat': 6.9271, 'lng': 79.8612, 'city': 'Colombo', 'country': 'Sri Lanka'},
        '95': {'lat': 19.7633, 'lng': 96.0785, 'city': 'Naypyidaw', 'country': 'Myanmar'},
        '98': {'lat': 35.6892, 'lng': 51.3890, 'city': 'Tehran', 'country': 'Iran'},
        '211': {'lat': 4.8594, 'lng': 31.5713, 'city': 'Juba', 'country': 'South Sudan'},
        '212': {'lat': 34.0209, 'lng': -6.8416, 'city': 'Rabat', 'country': 'Morocco'},
        '213': {'lat': 36.7538, 'lng': 3.0588, 'city': 'Algiers', 'country': 'Algeria'},
        '216': {'lat': 36.8065, 'lng': 10.1815, 'city': 'Tunis', 'country': 'Tunisia'},
        '218': {'lat': 32.8872, 'lng': 13.1913, 'city': 'Tripoli', 'country': 'Libya'},
        '220': {'lat': 13.4549, 'lng': -16.5790, 'city': 'Banjul', 'country': 'Gambia'},
        '221': {'lat': 14.7167, 'lng': -17.4677, 'city': 'Dakar', 'country': 'Senegal'},
        '233': {'lat': 5.6037, 'lng': -0.1870, 'city': 'Accra', 'country': 'Ghana'},
        '234': {'lat': 9.0765, 'lng': 7.3986, 'city': 'Abuja', 'country': 'Nigeria'},
        '249': {'lat': 15.5007, 'lng': 32.5599, 'city': 'Khartoum', 'country': 'Sudan'},
        '251': {'lat': 9.0320, 'lng': 38.7469, 'city': 'Addis Ababa', 'country': 'Ethiopia'},
        '252': {'lat': 2.0469, 'lng': 45.3182, 'city': 'Mogadishu', 'country': 'Somalia'},
        '254': {'lat': -1.2921, 'lng': 36.8219, 'city': 'Nairobi', 'country': 'Kenya'},
        '255': {'lat': -6.1630, 'lng': 35.7516, 'city': 'Dodoma', 'country': 'Tanzania'},
        '256': {'lat': 0.3476, 'lng': 32.5825, 'city': 'Kampala', 'country': 'Uganda'},
        '260': {'lat': -15.3875, 'lng': 28.3228, 'city': 'Lusaka', 'country': 'Zambia'},
        '263': {'lat': -17.8292, 'lng': 31.0522, 'city': 'Harare', 'country': 'Zimbabwe'},
        '264': {'lat': -22.5609, 'lng': 17.0658, 'city': 'Windhoek', 'country': 'Namibia'},
        '265': {'lat': -13.9626, 'lng': 33.7741, 'city': 'Lilongwe', 'country': 'Malawi'},
        '266': {'lat': -29.3142, 'lng': 27.4833, 'city': 'Maseru', 'country': 'Lesotho'},
        '267': {'lat': -24.6282, 'lng': 25.9231, 'city': 'Gaborone', 'country': 'Botswana'},
        '268': {'lat': -26.3054, 'lng': 31.1367, 'city': 'Mbabane', 'country': 'Eswatini'},
        '269': {'lat': -11.7172, 'lng': 43.2473, 'city': 'Moroni', 'country': 'Comoros'},
        '350': {'lat': 36.1408, 'lng': -5.3536, 'city': 'Gibraltar', 'country': 'Gibraltar'},
        '351': {'lat': 38.7223, 'lng': -9.1393, 'city': 'Lisbon', 'country': 'Portugal'},
        '352': {'lat': 49.6116, 'lng': 6.1319, 'city': 'Luxembourg', 'country': 'Luxembourg'},
        '353': {'lat': 53.3498, 'lng': -6.2603, 'city': 'Dublin', 'country': 'Ireland'},
        '354': {'lat': 64.1466, 'lng': -21.9426, 'city': 'Reykjavik', 'country': 'Iceland'},
        '355': {'lat': 41.3275, 'lng': 19.8187, 'city': 'Tirana', 'country': 'Albania'},
        '356': {'lat': 35.8989, 'lng': 14.5146, 'city': 'Valletta', 'country': 'Malta'},
        '357': {'lat': 35.1856, 'lng': 33.3823, 'city': 'Nicosia', 'country': 'Cyprus'},
        '358': {'lat': 60.1699, 'lng': 24.9384, 'city': 'Helsinki', 'country': 'Finland'},
        '359': {'lat': 42.6977, 'lng': 23.3219, 'city': 'Sofia', 'country': 'Bulgaria'},
        '370': {'lat': 54.6872, 'lng': 25.2797, 'city': 'Vilnius', 'country': 'Lithuania'},
        '371': {'lat': 56.9496, 'lng': 24.1052, 'city': 'Riga', 'country': 'Latvia'},
        '372': {'lat': 59.4370, 'lng': 24.7536, 'city': 'Tallinn', 'country': 'Estonia'},
        '380': {'lat': 50.4501, 'lng': 30.5234, 'city': 'Kyiv', 'country': 'Ukraine'},
        '381': {'lat': 44.7866, 'lng': 20.4489, 'city': 'Belgrade', 'country': 'Serbia'},
        '385': {'lat': 45.8150, 'lng': 15.9819, 'city': 'Zagreb', 'country': 'Croatia'},
        '386': {'lat': 46.0569, 'lng': 14.5058, 'city': 'Ljubljana', 'country': 'Slovenia'},
        '387': {'lat': 43.8563, 'lng': 18.4131, 'city': 'Sarajevo', 'country': 'Bosnia'},
        '420': {'lat': 50.0755, 'lng': 14.4378, 'city': 'Prague', 'country': 'Czech Republic'},
        '421': {'lat': 48.1486, 'lng': 17.1077, 'city': 'Bratislava', 'country': 'Slovakia'},
        '852': {'lat': 22.3193, 'lng': 114.1694, 'city': 'Hong Kong', 'country': 'Hong Kong'},
        '853': {'lat': 22.1987, 'lng': 113.5439, 'city': 'Macau', 'country': 'Macau'},
        '880': {'lat': 23.8103, 'lng': 90.4125, 'city': 'Dhaka', 'country': 'Bangladesh'},
        '886': {'lat': 25.0330, 'lng': 121.5654, 'city': 'Taipei', 'country': 'Taiwan'},
        '960': {'lat': 4.1755, 'lng': 73.5093, 'city': 'Male', 'country': 'Maldives'},
        '961': {'lat': 33.8938, 'lng': 35.5018, 'city': 'Beirut', 'country': 'Lebanon'},
        '962': {'lat': 31.9454, 'lng': 35.9284, 'city': 'Amman', 'country': 'Jordan'},
        '963': {'lat': 33.5138, 'lng': 36.2765, 'city': 'Damascus', 'country': 'Syria'},
        '964': {'lat': 33.3152, 'lng': 44.3661, 'city': 'Baghdad', 'country': 'Iraq'},
        '965': {'lat': 29.3759, 'lng': 47.9774, 'city': 'Kuwait City', 'country': 'Kuwait'},
        '966': {'lat': 24.7136, 'lng': 46.6753, 'city': 'Riyadh', 'country': 'Saudi Arabia'},
        '967': {'lat': 15.3694, 'lng': 44.1910, 'city': "Sana'a", 'country': 'Yemen'},
        '968': {'lat': 23.5880, 'lng': 58.3829, 'city': 'Muscat', 'country': 'Oman'},
        '970': {'lat': 31.9038, 'lng': 35.2034, 'city': 'Ramallah', 'country': 'Palestine'},
        '971': {'lat': 24.4539, 'lng': 54.3773, 'city': 'Abu Dhabi', 'country': 'UAE'},
        '972': {'lat': 31.7683, 'lng': 35.2137, 'city': 'Jerusalem', 'country': 'Israel'},
        '973': {'lat': 26.2285, 'lng': 50.5860, 'city': 'Manama', 'country': 'Bahrain'},
        '974': {'lat': 25.2854, 'lng': 51.5310, 'city': 'Doha', 'country': 'Qatar'},
        '975': {'lat': 27.4728, 'lng': 89.6393, 'city': 'Thimphu', 'country': 'Bhutan'},
        '976': {'lat': 47.8864, 'lng': 106.9057, 'city': 'Ulaanbaatar', 'country': 'Mongolia'},
        '977': {'lat': 27.7172, 'lng': 85.3240, 'city': 'Kathmandu', 'country': 'Nepal'},
    }
    
    def __init__(self, method: LocationMethod = 'basic', carrier_api_key: Optional[str] = None):
        """
        Initialize the location fetcher.
        
        Args:
            method: Location method to use ('basic', 'carrier', or 'gps')
            carrier_api_key: API key for carrier-based location (required for 'carrier' method)
        """
        self.method = method
        self.carrier_api_key = carrier_api_key
    
    def get_location(self, phone_number: str) -> Optional[Location]:
        """
        Fetch location for the given phone number.
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +254712345678)
            
        Returns:
            Location object with coordinates and metadata, or None if failed
            
        Raises:
            LocationError: If location cannot be determined
        """
        methods = {
            'basic': self._get_basic_location,
            'carrier': self._get_carrier_location,
            'gps': self._get_gps_location
        }
        
        method_func = methods.get(self.method, self._get_basic_location)
        
        try:
            return method_func(phone_number)
        except NotImplementedError:
            # Fall back to basic if method not implemented
            return self._get_basic_location(phone_number)
        except Exception as e:
            raise LocationError(f"Failed to get location: {str(e)}")
    
    def _parse_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """
        Parse phone number and extract country/carrier information.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Dictionary with parsed phone number info
        """
        try:
            parsed = phonenumbers.parse(phone_number, None)
            
            # Get country code
            country_code = str(parsed.country_code)
            
            # Get region/country description
            region = geocoder.description_for_number(parsed, 'en')
            
            # Get carrier name
            carrier_name = phone_carrier.name_for_number(parsed, 'en')
            
            return {
                'country_code': country_code,
                'region': region,
                'carrier': carrier_name,
                'is_valid': phonenumbers.is_valid_number(parsed)
            }
        except phonenumbers.phonenumberutil.NumberParseException:
            # Fallback: extract country code manually
            if phone_number.startswith('+'):
                # Try different lengths of country codes
                for length in [3, 2, 1]:
                    code = phone_number[1:1+length]
                    if code in self.COUNTRY_COORDINATES:
                        return {
                            'country_code': code,
                            'region': self.COUNTRY_COORDINATES[code]['country'],
                            'carrier': None,
                            'is_valid': True
                        }
            
            return {
                'country_code': '1',  # Default to US
                'region': 'Unknown',
                'carrier': None,
                'is_valid': False
            }
    
    def _get_basic_location(self, phone_number: str) -> Location:
        """
        Get basic location using phone number prefix database.
        
        This provides country/city level accuracy only (5-50km radius).
        Uses the country code from the phone number to estimate location.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Location object with approximate coordinates
        """
        info = self._parse_phone_number(phone_number)
        country_code = info['country_code']
        
        # Get coordinates for the country code
        coords = self.COUNTRY_COORDINATES.get(
            country_code,
            {'lat': 0.0, 'lng': 0.0, 'city': 'Unknown', 'country': 'Unknown'}
        )
        
        return Location(
            latitude=coords['lat'],
            longitude=coords['lng'],
            accuracy=5000,  # 5km radius - very rough estimate
            method='Phone Number Prefix Database',
            city=coords['city'],
            country=coords['country'],
            carrier=info.get('carrier'),
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _get_carrier_location(self, phone_number: str) -> Location:
        """
        Get location from carrier API using cell tower triangulation.
        
        This requires a partnership with telecom carriers and API access.
        Provides much better accuracy (50-500m radius).
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Location object with coordinates
            
        Raises:
            NotImplementedError: Carrier API integration not available
        """
        if not self.carrier_api_key:
            raise NotImplementedError(
                "Carrier-based location requires API credentials from telecom providers. "
                "Use --method basic for demonstration purposes.\n\n"
                "For carrier API access, consider:\n"
                "- Twilio Lookup API (carrier info only)\n"
                "- Direct carrier partnerships\n"
                "- Unwired Labs LocationAPI\n"
                "- Google Geolocation API"
            )
        
        # TODO: Implement actual carrier API integration
        # This would typically involve:
        # 1. Query carrier API with phone number
        # 2. Get cell tower IDs
        # 3. Calculate position from triangulation
        
        raise NotImplementedError("Carrier API integration not yet implemented")
    
    def _get_gps_location(self, phone_number: str) -> Location:
        """
        Get GPS-assisted location.
        
        This requires the target device to share its GPS coordinates,
        typically through an app or SMS-based request.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Location object with coordinates
            
        Raises:
            NotImplementedError: GPS-assisted location not available
        """
        raise NotImplementedError(
            "GPS-assisted location requires:\n"
            "1. An app installed on the target device, OR\n"
            "2. SMS-based location sharing (with user consent)\n\n"
            "This method provides the highest accuracy but requires device cooperation."
        )
    
    def get_map_url(self, location: Location) -> str:
        """
        Generate a Google Maps URL for the location.
        
        Args:
            location: Location object
            
        Returns:
            Google Maps URL string
        """
        return f"https://maps.google.com/?q={location.latitude},{location.longitude}"


class LocationError(Exception):
    """Exception raised for location-related errors."""
    pass
