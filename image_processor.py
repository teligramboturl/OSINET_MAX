"""
Image processing utilities for EXIF data extraction and OCR
"""

import io
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
import tempfile
import os

logger = logging.getLogger(__name__)

# Optional imports - gracefully handle missing dependencies
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - image processing will be limited")

try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False
    logger.warning("exifread not available - EXIF processing will be limited")

try:
    import pytesseract
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR libraries not available - text extraction disabled")

from utils import format_coordinates, get_google_maps_link, format_file_size

class ImageProcessor:
    """Process images to extract metadata and perform OCR"""
    
    def __init__(self):
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        
    async def process_image(self, image_data: Union[bytes, bytearray]) -> Optional[Dict[str, Any]]:
        """Process image and extract all available information"""
        try:
            if len(image_data) > self.max_image_size:
                return {"Error": "Image too large (max 10MB)"}
            
            result = {}
            
            # Basic image info
            basic_info = self._get_basic_image_info(image_data)
            if basic_info:
                result.update(basic_info)
            
            # EXIF data extraction
            exif_data = self._extract_exif_data(image_data)
            if exif_data:
                result["EXIF Data"] = exif_data
            
            # GPS coordinates
            gps_info = self._extract_gps_info(image_data)
            if gps_info:
                result["GPS Information"] = gps_info
            
            # OCR text extraction (if enabled)
            if OCR_AVAILABLE:
                ocr_text = self._extract_text_ocr(image_data)
                if ocr_text:
                    result["Extracted Text"] = ocr_text
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {"Error": f"Failed to process image: {str(e)}"}
    
    def _get_basic_image_info(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Get basic image information"""
        try:
            if not PIL_AVAILABLE:
                return {"File Size": format_file_size(len(image_data))}
            
            image = Image.open(io.BytesIO(image_data))
            
            info = {
                "📁 File Size": format_file_size(len(image_data)),
                "📐 Dimensions": f"{image.width} x {image.height}",
                "🎨 Format": image.format or "Unknown",
                "🔢 Mode": image.mode,
            }
            
            # Additional format-specific info
            if hasattr(image, 'info') and image.info:
                if 'dpi' in image.info:
                    info["📏 DPI"] = str(image.info['dpi'])
                if 'quality' in image.info:
                    info["⭐ Quality"] = str(image.info['quality'])
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting basic image info: {e}")
            return None
    
    def _extract_exif_data(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Extract EXIF metadata from image"""
        try:
            if not PIL_AVAILABLE:
                return self._extract_exif_with_exifread(image_data)
            
            image = Image.open(io.BytesIO(image_data))
            exif_data = image._getexif()
            
            if not exif_data:
                return None
            
            exif_info = {}
            
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Skip GPS info (handled separately)
                if tag == 'GPSInfo':
                    continue
                
                # Format common EXIF tags
                if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                    try:
                        exif_info[f"📅 {tag}"] = str(value)
                    except:
                        exif_info[f"📅 {tag}"] = "Invalid date"
                elif tag in ['Make', 'Model']:
                    exif_info[f"📱 {tag}"] = str(value)
                elif tag in ['Software']:
                    exif_info[f"💻 {tag}"] = str(value)
                elif tag in ['ImageWidth', 'ImageLength']:
                    exif_info[f"📐 {tag}"] = str(value)
                elif tag in ['Orientation']:
                    orientation_map = {
                        1: "Normal", 2: "Mirrored", 3: "Rotated 180°",
                        4: "Mirrored and rotated 180°", 5: "Mirrored and rotated 90° CCW",
                        6: "Rotated 90° CW", 7: "Mirrored and rotated 90° CW",
                        8: "Rotated 90° CCW"
                    }
                    exif_info[f"🔄 {tag}"] = orientation_map.get(value, str(value))
                elif tag in ['Flash']:
                    flash_map = {
                        0: "No Flash", 1: "Flash", 5: "Flash, no strobe return",
                        7: "Flash, strobe return", 9: "Flash, compulsory",
                        13: "Flash, compulsory, no return", 15: "Flash, compulsory, return",
                        16: "No Flash, compulsory", 24: "No Flash, auto",
                        25: "Flash, auto", 29: "Flash, auto, no return",
                        31: "Flash, auto, return"
                    }
                    exif_info[f"⚡ {tag}"] = flash_map.get(value, str(value))
                else:
                    # Include other potentially useful tags
                    if isinstance(value, (str, int, float)) and len(str(value)) < 100:
                        exif_info[f"ℹ️ {tag}"] = str(value)
            
            return exif_info if exif_info else None
            
        except Exception as e:
            logger.error(f"Error extracting EXIF data: {e}")
            return None
    
    def _extract_exif_with_exifread(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Extract EXIF data using exifread library"""
        try:
            if not EXIFREAD_AVAILABLE:
                return None
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, 'rb') as f:
                    tags = exifread.process_file(f)
                
                if not tags:
                    return None
                
                exif_info = {}
                
                # Process relevant tags
                for tag, value in tags.items():
                    if tag.startswith('EXIF') or tag.startswith('Image'):
                        key = tag.replace('EXIF ', '').replace('Image ', '')
                        exif_info[f"ℹ️ {key}"] = str(value)
                
                return exif_info if exif_info else None
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error extracting EXIF with exifread: {e}")
            return None
    
    def _extract_gps_info(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Extract GPS information from image"""
        try:
            if not PIL_AVAILABLE:
                return None
            
            image = Image.open(io.BytesIO(image_data))
            exif_data = image._getexif()
            
            if not exif_data or 'GPSInfo' not in exif_data:
                return None
            
            gps_info = {}
            gps_data = exif_data['GPSInfo']
            
            # Extract GPS coordinates
            lat, lon = self._get_coordinates(gps_data)
            
            if lat is not None and lon is not None:
                gps_info["📍 Coordinates"] = format_coordinates(lat, lon)
                gps_info["🗺️ Google Maps"] = get_google_maps_link(lat, lon)
            
            # Extract other GPS information
            gps_tags = {
                0: "GPS Version",
                1: "Latitude Ref",
                2: "Latitude",
                3: "Longitude Ref",
                4: "Longitude",
                5: "Altitude Ref",
                6: "Altitude",
                7: "Time Stamp",
                8: "GPS Satellites",
                9: "GPS Receiver Status",
                10: "GPS Measurement Mode",
                11: "GPS DOP",
                12: "Speed Ref",
                13: "Speed",
                14: "Track Ref",
                15: "Track",
                16: "Image Direction Ref",
                17: "Image Direction",
                18: "Map Datum",
                29: "GPS Date"
            }
            
            for tag_id, tag_name in gps_tags.items():
                if tag_id in gps_data:
                    value = gps_data[tag_id]
                    if tag_name in ["Altitude", "Speed"]:
                        gps_info[f"📏 {tag_name}"] = f"{value} meters" if tag_name == "Altitude" else f"{value} km/h"
                    elif tag_name not in ["Latitude", "Longitude", "Latitude Ref", "Longitude Ref"]:
                        gps_info[f"🛰️ {tag_name}"] = str(value)
            
            return gps_info if gps_info else None
            
        except Exception as e:
            logger.error(f"Error extracting GPS info: {e}")
            return None
    
    def _get_coordinates(self, gps_data: Dict) -> tuple:
        """Convert GPS data to decimal coordinates"""
        try:
            def convert_to_degrees(value):
                """Convert GPS coordinate to decimal degrees"""
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    degrees = float(value[0])
                    minutes = float(value[1])
                    seconds = float(value[2])
                    return degrees + minutes / 60 + seconds / 3600
                return float(value)
            
            lat = None
            lon = None
            
            if 2 in gps_data and 1 in gps_data:  # Latitude
                lat = convert_to_degrees(gps_data[2])
                if gps_data[1] == 'S':
                    lat = -lat
            
            if 4 in gps_data and 3 in gps_data:  # Longitude
                lon = convert_to_degrees(gps_data[4])
                if gps_data[3] == 'W':
                    lon = -lon
            
            return lat, lon
            
        except Exception as e:
            logger.error(f"Error converting GPS coordinates: {e}")
            return None, None
    
    def _extract_text_ocr(self, image_data: bytes) -> Optional[str]:
        """Extract text from image using OCR"""
        try:
            if not OCR_AVAILABLE:
                return None
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return None
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply some basic preprocessing
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Extract text
            text = pytesseract.image_to_string(gray, config='--psm 6')
            
            # Clean up the text
            text = text.strip()
            if len(text) < 3:  # Too short to be meaningful
                return None
            
            # Remove excessive whitespace
            import re
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r' +', ' ', text)
            
            return text if text else None
            
        except Exception as e:
            logger.error(f"Error extracting text with OCR: {e}")
            return None
