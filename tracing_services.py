"""
Services for phone tracing and vehicle lookup
"""

import asyncio
import logging
import re
from typing import Dict, Any, Union, Optional

import requests
from bs4 import BeautifulSoup

from config import Config
from utils import clean_text, extract_numbers

logger = logging.getLogger(__name__)

class TracingService:
    """Service class for phone tracing and vehicle lookup"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(self.config.get_request_headers())
        
        # Comprehensive state and RTO codes mapping
        self.state_codes = {
            'AP': 'Andhra Pradesh', 'AR': 'Arunachal Pradesh', 'AS': 'Assam', 'BR': 'Bihar',
            'CG': 'Chhattisgarh', 'GA': 'Goa', 'GJ': 'Gujarat', 'HR': 'Haryana',
            'HP': 'Himachal Pradesh', 'JH': 'Jharkhand', 'KA': 'Karnataka', 'KL': 'Kerala',
            'MP': 'Madhya Pradesh', 'MH': 'Maharashtra', 'MN': 'Manipur', 'ML': 'Meghalaya',
            'MZ': 'Mizoram', 'NL': 'Nagaland', 'OD': 'Odisha', 'PB': 'Punjab',
            'RJ': 'Rajasthan', 'SK': 'Sikkim', 'TN': 'Tamil Nadu', 'TG': 'Telangana',
            'TR': 'Tripura', 'UK': 'Uttarakhand', 'UP': 'Uttar Pradesh', 'WB': 'West Bengal',
            'AN': 'Andaman & Nicobar Islands', 'CH': 'Chandigarh', 'DH': 'Dadra & Nagar Haveli',
            'DD': 'Daman & Diu', 'DL': 'Delhi', 'LD': 'Lakshadweep', 'PY': 'Puducherry'
        }
        
        # RTO office mapping
        self.rto_offices = {
            # Maharashtra
            'MH01': 'Mumbai Central RTO', 'MH02': 'Mumbai West RTO', 'MH03': 'Mumbai East RTO',
            'MH04': 'Mumbai South RTO', 'MH05': 'Thane RTO', 'MH06': 'Raigad RTO',
            'MH07': 'Ratnagiri RTO', 'MH08': 'Kolhapur RTO', 'MH09': 'Pune RTO',
            'MH10': 'Sangli RTO', 'MH11': 'Solapur RTO', 'MH12': 'Aurangabad RTO',
            'MH13': 'Nashik RTO', 'MH14': 'Dhule RTO', 'MH15': 'Jalgaon RTO',
            'MH16': 'Nagpur Central RTO', 'MH17': 'Nagpur East RTO', 'MH18': 'Bhandara RTO',
            'MH19': 'Amravati RTO', 'MH20': 'Buldhana RTO', 'MH21': 'Akola RTO',
            'MH22': 'Washim RTO', 'MH23': 'Yavatmal RTO', 'MH31': 'Chandrapur RTO',
            'MH43': 'Pune East RTO', 'MH46': 'Satara RTO', 'MH47': 'Nanded RTO',
            
            # Delhi
            'DL01': 'Delhi Central RTO', 'DL02': 'Delhi West RTO', 'DL03': 'Delhi East RTO',
            'DL04': 'Delhi South RTO', 'DL05': 'Delhi North RTO', 'DL06': 'Rohini RTO',
            'DL07': 'New Delhi RTO', 'DL08': 'Dwarka RTO', 'DL09': 'Outer Delhi RTO',
            'DL10': 'Shahdara RTO', 'DL11': 'South West Delhi RTO', 'DL12': 'North West Delhi RTO',
            'DL13': 'North East Delhi RTO', 'DL14': 'South East Delhi RTO',
            
            # Karnataka
            'KA01': 'Bangalore Central RTO', 'KA02': 'Bangalore North RTO', 'KA03': 'Bangalore South RTO',
            'KA04': 'Bangalore East RTO', 'KA05': 'Bangalore West RTO', 'KA06': 'Tumkur RTO',
            'KA07': 'Mysore RTO', 'KA08': 'Bellary RTO', 'KA09': 'Mangalore RTO',
            'KA10': 'Hubli RTO', 'KA11': 'Gulbarga RTO', 'KA12': 'Belgaum RTO',
            'KA51': 'BBMP East RTO', 'KA52': 'BBMP West RTO', 'KA53': 'BBMP North RTO',
            
            # Tamil Nadu
            'TN01': 'Chennai Central RTO', 'TN02': 'Chennai North RTO', 'TN03': 'Chennai South RTO',
            'TN04': 'Chennai West RTO', 'TN05': 'Chennai East RTO', 'TN06': 'Thiruvallur RTO',
            'TN07': 'Kanchipuram RTO', 'TN08': 'Vellore RTO', 'TN09': 'Tiruvannamalai RTO',
            'TN10': 'Villupuram RTO', 'TN11': 'Cuddalore RTO', 'TN12': 'Chidambaram RTO',
            
            # Uttar Pradesh
            'UP01': 'Agra RTO', 'UP02': 'Aligarh RTO', 'UP03': 'Allahabad RTO',
            'UP04': 'Ambedkar Nagar RTO', 'UP05': 'Amethi RTO', 'UP06': 'Amroha RTO',
            'UP07': 'Auraiya RTO', 'UP08': 'Azamgarh RTO', 'UP09': 'Baghpat RTO',
            'UP10': 'Bahraich RTO', 'UP11': 'Ballia RTO', 'UP12': 'Balrampur RTO',
            'UP13': 'Banda RTO', 'UP14': 'Barabanki RTO', 'UP15': 'Bareilly RTO',
            'UP16': 'Basti RTO', 'UP17': 'Bhadohi RTO', 'UP18': 'Bijnor RTO',
            'UP19': 'Budaun RTO', 'UP20': 'Bulandshahr RTO', 'UP21': 'Chandauli RTO',
            'UP22': 'Chitrakoot RTO', 'UP23': 'Deoria RTO', 'UP24': 'Etah RTO',
            'UP25': 'Etawah RTO', 'UP26': 'Faizabad RTO', 'UP27': 'Farrukhabad RTO',
            'UP28': 'Fatehpur RTO', 'UP29': 'Firozabad RTO', 'UP30': 'Gautam Buddha Nagar RTO',
            'UP31': 'Ghaziabad RTO', 'UP32': 'Ghazipur RTO', 'UP33': 'Gonda RTO',
            'UP34': 'Gorakhpur RTO', 'UP35': 'Hamirpur RTO', 'UP36': 'Hapur RTO',
            'UP37': 'Hardoi RTO', 'UP38': 'Hathras RTO', 'UP39': 'Jalaun RTO',
            'UP40': 'Jaunpur RTO', 'UP41': 'Jhansi RTO', 'UP42': 'Kannauj RTO',
            'UP43': 'Kanpur Dehat RTO', 'UP44': 'Kanpur Nagar RTO', 'UP45': 'Kasganj RTO',
            'UP46': 'Kaushambi RTO', 'UP47': 'Kheri RTO', 'UP48': 'Kushinagar RTO',
            'UP49': 'Lalitpur RTO', 'UP50': 'Lucknow RTO', 'UP51': 'Maharajganj RTO',
            'UP52': 'Mahoba RTO', 'UP53': 'Mainpuri RTO', 'UP54': 'Mathura RTO',
            'UP55': 'Mau RTO', 'UP56': 'Meerut RTO', 'UP57': 'Mirzapur RTO',
            'UP58': 'Moradabad RTO', 'UP59': 'Muzaffarnagar RTO', 'UP60': 'Pilibhit RTO',
            'UP61': 'Pratapgarh RTO', 'UP62': 'Raebareli RTO', 'UP63': 'Rampur RTO',
            'UP64': 'Saharanpur RTO', 'UP65': 'Sambhal RTO', 'UP66': 'Sant Kabir Nagar RTO',
            'UP67': 'Shahjahanpur RTO', 'UP68': 'Shamli RTO', 'UP69': 'Shravasti RTO',
            'UP70': 'Siddharthnagar RTO', 'UP71': 'Sitapur RTO', 'UP72': 'Sonbhadra RTO',
            'UP73': 'Sultanpur RTO', 'UP74': 'Unnao RTO', 'UP75': 'Varanasi RTO',
            
            # West Bengal
            'WB01': 'Kolkata Central RTO', 'WB02': 'Kolkata South RTO', 'WB03': 'Kolkata North RTO',
            'WB04': 'Howrah RTO', 'WB05': 'Hooghly RTO', 'WB06': '24 Parganas North RTO',
            'WB07': '24 Parganas South RTO', 'WB08': 'Nadia RTO', 'WB09': 'Murshidabad RTO',
            'WB10': 'Birbhum RTO', 'WB11': 'Burdwan East RTO', 'WB12': 'Burdwan West RTO',
            'WB13': 'Malda RTO', 'WB14': 'Dinajpur North RTO', 'WB15': 'Dinajpur South RTO',
            'WB16': 'Jalpaiguri RTO', 'WB17': 'Darjeeling RTO', 'WB18': 'Cooch Behar RTO',
            'WB19': 'Alipurduar RTO', 'WB20': 'Kalimpong RTO', 'WB21': 'Bankura RTO',
            'WB22': 'Purulia RTO', 'WB23': 'Paschim Medinipur RTO', 'WB24': 'Purba Medinipur RTO',
            'WB25': 'Jhargram RTO'
        }
    
    async def trace_phone_number(self, phone_number: str) -> Union[Dict[str, Any], str]:
        """Trace phone number using multiple sources"""
        try:
            # Clean and format phone number
            cleaned_number = re.sub(r'[^\d+]', '', phone_number)
            
            # Try multiple tracing methods
            methods = [
                self._trace_calltracer,
                self._trace_truecaller_info,
                self._trace_basic_info
            ]
            
            for method in methods:
                try:
                    result = await method(cleaned_number)
                    if isinstance(result, dict) and result:
                        return result
                except Exception as e:
                    logger.warning(f"Tracing method {method.__name__} failed: {e}")
                    continue
            
            return "❌ Unable to trace this phone number. Please try again later."
        
        except Exception as e:
            logger.error(f"Error tracing phone number: {e}")
            return f"❌ Tracing failed: {str(e)}"
    
    async def _trace_calltracer(self, phone_number: str) -> Union[Dict[str, Any], str]:
        """Trace phone number using calltracer.in"""
        try:
            url = "https://calltracer.in"
            payload = {"country": "IN", "q": phone_number}
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.session.post(url, data=payload, timeout=self.config.REQUEST_TIMEOUT)
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                return self._parse_calltracer_response(soup, phone_number)
            else:
                return f"❌ Request failed with status code: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Calltracer tracing failed: {e}")
            raise
    
    def _parse_calltracer_response(self, soup: BeautifulSoup, phone_number: str) -> Dict[str, Any]:
        """Parse calltracer response"""
        details = {"📞 Number": phone_number}
        
        # Fields to extract
        fields = [
            ("❗️ Complaints", "Complaints"),
            ("👤 Owner Name", "Owner Name"),
            ("📶 SIM Card", "SIM card"),
            ("📍 Mobile State", "Mobile State"),
            ("🔑 IMEI Number", "IMEI number"),
            ("🌐 MAC Address", "MAC address"),
            ("⚡️ Connection", "Connection"),
            ("🌍 IP Address", "IP address"),
            ("🏠 Owner Address", "Owner Address"),
            ("🏘 Hometown", "Hometown"),
            ("🗺 Reference City", "Refrence City"),
            ("👥 Owner Personality", "Owner Personality"),
            ("🗣 Language", "Language"),
            ("📡 Mobile Locations", "Mobile Locations"),
            ("🌎 Country", "Country"),
            ("📜 Tracking History", "Tracking History"),
            ("🆔 Tracker ID", "Tracker Id"),
            ("📶 Tower Locations", "Tower Locations")
        ]
        
        for display_name, search_text in fields:
            try:
                element = soup.find(string=search_text)
                if element:
                    value = element.find_next("td")
                    if value:
                        details[display_name] = clean_text(value.get_text())
                    else:
                        details[display_name] = "N/A"
                else:
                    details[display_name] = "N/A"
            except Exception as e:
                logger.warning(f"Failed to extract {display_name}: {e}")
                details[display_name] = "N/A"
        
        return details
    
    async def _trace_truecaller_info(self, phone_number: str) -> Union[Dict[str, Any], str]:
        """Get basic phone number info (carrier, location, etc.)"""
        try:
            # This is a placeholder for basic phone number analysis
            # In a real implementation, you would use APIs or other sources
            details = {"📞 Number": phone_number}
            
            # Basic analysis based on number format
            if phone_number.startswith('+91') or (len(phone_number) == 10 and phone_number.startswith(('6', '7', '8', '9'))):
                details["🌎 Country"] = "India"
                details["📍 Region"] = self._get_indian_region(phone_number)
                details["📶 Network Type"] = "Mobile"
            elif phone_number.startswith('+1'):
                details["🌎 Country"] = "United States/Canada"
                details["📶 Network Type"] = "Mobile/Landline"
            elif phone_number.startswith('+44'):
                details["🌎 Country"] = "United Kingdom"
                details["📶 Network Type"] = "Mobile/Landline"
            else:
                details["🌎 Country"] = "Unknown"
                details["📶 Network Type"] = "Unknown"
            
            return details
            
        except Exception as e:
            logger.error(f"Basic info tracing failed: {e}")
            raise
    
    async def _trace_basic_info(self, phone_number: str) -> Dict[str, Any]:
        """Get basic phone number information"""
        details = {"📞 Number": phone_number}
        
        # Analyze number format
        if phone_number.startswith('+'):
            details["📞 Format"] = "International"
        else:
            details["📞 Format"] = "Local"
        
        # Basic number analysis
        if len(phone_number.replace('+', '').replace(' ', '')) >= 10:
            details["✅ Validity"] = "Valid Length"
        else:
            details["✅ Validity"] = "Invalid Length"
        
        # Number type detection
        if any(phone_number.endswith(suffix) for suffix in ['0000', '1111', '2222']):
            details["⚠️ Type"] = "Possibly Fake/Test Number"
        else:
            details["⚠️ Type"] = "Regular Number"
        
        return details
    
    def _get_indian_region(self, phone_number: str) -> str:
        """Get Indian region based on phone number"""
        # Remove country code
        number = phone_number.replace('+91', '').replace(' ', '')
        
        if len(number) >= 10:
            # Basic region mapping based on first few digits
            first_digit = number[0]
            if first_digit == '9':
                return "Northern/Western India"
            elif first_digit == '8':
                return "Eastern/Southern India"
            elif first_digit == '7':
                return "Central/Western India"
            elif first_digit == '6':
                return "Eastern India"
        
        return "Unknown Region"
    
    async def lookup_vehicle_info(self, vehicle_number: str) -> Union[Dict[str, Any], str]:
        """Lookup vehicle information"""
        try:
            # Clean vehicle number
            vehicle_number = vehicle_number.upper().replace(' ', '').replace('-', '')
            
            # Parse vehicle number format
            parsed_info = self._parse_vehicle_number(vehicle_number)
            
            if not parsed_info:
                return "❌ Invalid vehicle registration format"
            
            # Get detailed information
            vehicle_info = self._get_vehicle_details(parsed_info)
            
            return vehicle_info
            
        except Exception as e:
            logger.error(f"Error looking up vehicle: {e}")
            return f"❌ Vehicle lookup failed: {str(e)}"
    
    def _parse_vehicle_number(self, vehicle_number: str) -> Optional[Dict[str, Any]]:
        """Parse vehicle registration number"""
        try:
            # Standard format: STATE_CODE + DISTRICT_CODE + SERIES + NUMBER
            # Example: MH01AB1234, DL05CD5678
            
            patterns = [
                r'^([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{4})$',  # Standard format
                r'^([A-Z]{2})(\d{2})([A-Z]{1,2})(\d{1,4})$',  # Variable digit format
                r'^([A-Z]{2})(\d{1,2})([A-Z]{1,2})(\d{1,4})$'  # Single digit district
            ]
            
            for pattern in patterns:
                match = re.match(pattern, vehicle_number)
                if match:
                    state_code = match.group(1)
                    district_code = match.group(2)
                    series = match.group(3)
                    number = match.group(4)
                    
                    rto_code = f"{state_code}{district_code.zfill(2)}"
                    
                    return {
                        'original': vehicle_number,
                        'state_code': state_code,
                        'district_code': district_code,
                        'series': series,
                        'number': number,
                        'rto_code': rto_code
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing vehicle number: {e}")
            return None
    
    def _get_vehicle_details(self, parsed_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed vehicle information"""
        details = {
            "🚗 Registration Number": parsed_info['original'],
            "🏛️ State": self.state_codes.get(parsed_info['state_code'], 'Unknown State'),
            "🏢 RTO Office": self.rto_offices.get(parsed_info['rto_code'], 'Unknown RTO'),
            "🆔 RTO Code": parsed_info['rto_code'],
            "📊 Series": parsed_info['series'],
            "🔢 Number": parsed_info['number'],
            "📍 Registration Region": f"{parsed_info['state_code']}-{parsed_info['district_code']}"
        }
        
        # Add vehicle type information based on series
        vehicle_type = self._get_vehicle_type(parsed_info['series'])
        if vehicle_type:
            details["🚙 Vehicle Type"] = vehicle_type
        
        # Add registration year estimation
        reg_year = self._estimate_registration_year(parsed_info)
        if reg_year:
            details["📅 Estimated Registration Year"] = reg_year
        
        return details
    
    def _get_vehicle_type(self, series: str) -> Optional[str]:
        """Determine vehicle type based on series"""
        # This is a basic classification
        if len(series) == 1:
            return "Private Vehicle (Old Format)"
        elif len(series) == 2:
            first_char = series[0]
            if first_char in ['A', 'B', 'C', 'D']:
                return "Private Vehicle"
            elif first_char in ['E', 'F', 'G', 'H']:
                return "Taxi/Commercial"
            elif first_char in ['P', 'Q', 'R', 'S']:
                return "Private Vehicle"
            elif first_char in ['T', 'U', 'V', 'W']:
                return "Two Wheeler"
            elif first_char in ['X', 'Y', 'Z']:
                return "Special Vehicle"
        
        return None
    
    def _estimate_registration_year(self, parsed_info: Dict[str, Any]) -> Optional[str]:
        """Estimate registration year based on number"""
        # This is a rough estimation and may not be accurate
        # Different states have different numbering systems
        try:
            number = int(parsed_info['number'])
            if number < 1000:
                return "Before 2005 (Estimated)"
            elif number < 5000:
                return "2005-2010 (Estimated)"
            elif number < 9000:
                return "2010-2015 (Estimated)"
            else:
                return "After 2015 (Estimated)"
        except:
            return None
