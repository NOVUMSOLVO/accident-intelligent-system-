#!/usr/bin/env python3
"""
Person Identification Engine
Handles license plate recognition, reverse lookup, and person identification
"""

import json
from dataclasses import dataclass

import requests
from neo4j import GraphDatabase
from twilio.base.exceptions import TwilioException
from twilio.rest import Client as TwilioClient

from ..utils.config import Config
from ..utils.logger import StructuredLogger


@dataclass
class VehicleInfo:
    """Vehicle information from license plate lookup"""

    plate: str
    state: str
    make: str
    model: str
    year: int
    color: str
    vin: str
    registration_date: str
    owner_id: Optional[str] = None


@dataclass
class PersonInfo:
    """Person information from various sources"""

    person_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    social_profiles: List[Dict] = None
    confidence_score: float = 0.0
    sources: List[str] = None

    def __post_init__(self):
        if self.social_profiles is None:
            self.social_profiles = []
        if self.sources is None:
            self.sources = []


class OpenALPRClient:
    """Client for OpenALPR license plate recognition service"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.base_url = "https://api.openalpr.com/v3"
        self.logger = StructuredLogger(__name__)

    def recognize_plate(self, image_url: str, state: str = None) -> List[Dict]:
        """Recognize license plate from image URL"""
        try:
            url = f"{self.base_url}/recognize"

            params = {
                "secret_key": self.secret_key,
                "recognize_vehicle": 1,
                "country": "us",
                "return_image": 0,
                "topn": 5,
            }

            if state:
                params["state"] = state

            data = {"image_url": image_url}

            start_time = time.time()
            response = requests.post(url, data=data, params=params, timeout=30)
            response_time = time.time() - start_time

            self.logger.log_api_call(
                api_name="OpenALPR",
                endpoint="recognize",
                status_code=response.status_code,
                response_time=response_time,
                image_url=image_url,
            )

            if response.status_code == 200:
                result = response.json()
                return self._parse_alpr_response(result)
            else:
                self.logger.error(
                    f"OpenALPR API error: {response.status_code} - {response.text}"
                )
                return []

        except Exception as e:
            self.logger.error(f"Error calling OpenALPR API: {e}")
            return []

    def _parse_alpr_response(self, response: Dict) -> List[Dict]:
        """Parse OpenALPR API response"""
        plates = []

        for result in response.get("results", []):
            for candidate in result.get("candidates", []):
                plate_info = {
                    "plate": candidate.get("plate", ""),
                    "confidence": candidate.get("confidence", 0),
                    "region": result.get("region", ""),
                    "processing_time": response.get("processing_time_ms", 0),
                }

                # Add vehicle information if available
                vehicle = result.get("vehicle", {})
                if vehicle:
                    plate_info.update(
                        {
                            "vehicle_make": (
                                vehicle.get("make", [{}])[0].get("name", "")
                                if vehicle.get("make")
                                else ""
                            ),
                            "vehicle_color": (
                                vehicle.get("color", [{}])[0].get("name", "")
                                if vehicle.get("color")
                                else ""
                            ),
                            "vehicle_year": (
                                vehicle.get("year", [{}])[0].get("name", "")
                                if vehicle.get("year")
                                else ""
                            ),
                        }
                    )

                plates.append(plate_info)

        return plates


class VehicleRegistrationLookup:
    """Handles vehicle registration data lookup"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.datatier_api_key = config.datatier_api_key
        self.been_verified_api_key = config.been_verified_api_key

    def lookup_vehicle_by_plate(self, plate: str, state: str) -> Optional[VehicleInfo]:
        """Lookup vehicle information by license plate"""
        # Try DataTier API first
        vehicle_info = self._lookup_datatier(plate, state)
        if vehicle_info:
            return vehicle_info

        # Fallback to BeenVerified API
        vehicle_info = self._lookup_been_verified(plate, state)
        return vehicle_info

    def _lookup_datatier(self, plate: str, state: str) -> Optional[VehicleInfo]:
        """Lookup vehicle using DataTier API"""
        if not self.datatier_api_key:
            return None

        try:
            url = "https://api.datatier.org/v1/vehicle/lookup"
            headers = {
                "Authorization": f"Bearer {self.datatier_api_key}",
                "Content-Type": "application/json",
            }

            data = {"license_plate": plate, "state": state}

            start_time = time.time()
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response_time = time.time() - start_time

            self.logger.log_api_call(
                api_name="DataTier",
                endpoint="vehicle/lookup",
                status_code=response.status_code,
                response_time=response_time,
                plate=plate,
                state=state,
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_datatier_response(data)

        except Exception as e:
            self.logger.error(f"Error calling DataTier API: {e}")

        return None

    def _lookup_been_verified(self, plate: str, state: str) -> Optional[VehicleInfo]:
        """Lookup vehicle using BeenVerified API"""
        if not self.been_verified_api_key:
            return None

        try:
            url = "https://api.beenverified.com/v1/vehicle"
            params = {
                "api_key": self.been_verified_api_key,
                "license_plate": plate,
                "state": state,
            }

            start_time = time.time()
            response = requests.get(url, params=params, timeout=30)
            response_time = time.time() - start_time

            self.logger.log_api_call(
                api_name="BeenVerified",
                endpoint="vehicle",
                status_code=response.status_code,
                response_time=response_time,
                plate=plate,
                state=state,
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_been_verified_response(data)

        except Exception as e:
            self.logger.error(f"Error calling BeenVerified API: {e}")

        return None

    def _parse_datatier_response(self, data: Dict) -> Optional[VehicleInfo]:
        """Parse DataTier API response"""
        try:
            vehicle_data = data.get("vehicle", {})
            return VehicleInfo(
                plate=vehicle_data.get("license_plate", ""),
                state=vehicle_data.get("state", ""),
                make=vehicle_data.get("make", ""),
                model=vehicle_data.get("model", ""),
                year=int(vehicle_data.get("year", 0)),
                color=vehicle_data.get("color", ""),
                vin=vehicle_data.get("vin", ""),
                registration_date=vehicle_data.get("registration_date", ""),
                owner_id=vehicle_data.get("owner_id"),
            )
        except Exception as e:
            self.logger.error(f"Error parsing DataTier response: {e}")
            return None

    def _parse_been_verified_response(self, data: Dict) -> Optional[VehicleInfo]:
        """Parse BeenVerified API response"""
        try:
            return VehicleInfo(
                plate=data.get("license_plate", ""),
                state=data.get("state", ""),
                make=data.get("make", ""),
                model=data.get("model", ""),
                year=int(data.get("year", 0)),
                color=data.get("color", ""),
                vin=data.get("vin", ""),
                registration_date=data.get("registration_date", ""),
                owner_id=data.get("owner_id"),
            )
        except Exception as e:
            self.logger.error(f"Error parsing BeenVerified response: {e}")
            return None


class Neo4jVehicleOwnerGraph:
    """Neo4j graph database for vehicle-owner relationships"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)
        self.driver = GraphDatabase.driver(
            config.neo4j_uri, auth=(config.neo4j_user, config.neo4j_password)
        )

    def find_owner_by_vehicle(
        self, plate: str, state: str = None
    ) -> Optional[PersonInfo]:
        """Find vehicle owner using Neo4j graph query"""
        try:
            with self.driver.session() as session:
                # Neo4j query to find owner-vehicle relationship
                query = """
                MATCH (o:Owner)-[r:OWNS]->(v:Vehicle)
                WHERE v.plate = $plate
                AND ($state IS NULL OR v.state = $state)
                RETURN o.name as name, o.phone as phone, o.email as email,
                       o.address as address, o.age as age, o.person_id as person_id,
                       r.purchase_date as purchase_date, r.confidence as confidence
                ORDER BY r.confidence DESC
                LIMIT 1
                """

                result = session.run(query, plate=plate, state=state)
                record = result.single()

                if record:
                    return PersonInfo(
                        person_id=record["person_id"] or "",
                        name=record["name"] or "",
                        phone=record["phone"],
                        email=record["email"],
                        address=record["address"],
                        age=record["age"],
                        confidence_score=record["confidence"] or 0.0,
                        sources=["neo4j_graph"],
                    )

                return None

        except Exception as e:
            self.logger.error(f"Error querying Neo4j for vehicle owner: {e}")
            return None

    def create_vehicle_owner_relationship(
        self, vehicle: VehicleInfo, person: PersonInfo, confidence: float = 1.0
    ):
        """Create or update vehicle-owner relationship in Neo4j"""
        try:
            with self.driver.session() as session:
                query = """
                MERGE (v:Vehicle {plate: $plate, state: $state})
                SET v.make = $make, v.model = $model, v.year = $year,
                    v.color = $color, v.vin = $vin, v.registration_date = $registration_date
                
                MERGE (o:Owner {person_id: $person_id})
                SET o.name = $name, o.phone = $phone, o.email = $email,
                    o.address = $address, o.age = $age
                
                MERGE (o)-[r:OWNS]->(v)
                SET r.confidence = $confidence, r.updated_at = datetime()
                """

                session.run(
                    query,
                    plate=vehicle.plate,
                    state=vehicle.state,
                    make=vehicle.make,
                    model=vehicle.model,
                    year=vehicle.year,
                    color=vehicle.color,
                    vin=vehicle.vin,
                    registration_date=vehicle.registration_date,
                    person_id=person.person_id,
                    name=person.name,
                    phone=person.phone,
                    email=person.email,
                    address=person.address,
                    age=person.age,
                    confidence=confidence,
                )

                self.logger.log_database_operation(
                    database="neo4j",
                    operation="create_relationship",
                    collection_table="Owner-OWNS-Vehicle",
                    affected_rows=1,
                    execution_time=0,
                    plate=vehicle.plate,
                    person_id=person.person_id,
                )

        except Exception as e:
            self.logger.error(f"Error creating vehicle-owner relationship: {e}")

    def close(self):
        """Close Neo4j driver"""
        if self.driver:
            self.driver.close()


class PhoneValidator:
    """Phone number validation using Twilio Lookup API"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        if config.twilio_account_sid and config.twilio_auth_token:
            self.client = TwilioClient(
                config.twilio_account_sid, config.twilio_auth_token
            )
        else:
            self.client = None
            self.logger.warning("Twilio credentials not configured")

    def validate_phone(self, phone_number: str) -> Dict:
        """Validate phone number using Twilio Lookup API"""
        if not self.client:
            return {"valid": False, "error": "Twilio not configured"}

        try:
            start_time = time.time()
            phone_number_info = self.client.lookups.phone_numbers(phone_number).fetch(
                type=["carrier", "caller-name"]
            )
            response_time = time.time() - start_time

            self.logger.log_api_call(
                api_name="Twilio",
                endpoint="lookups",
                status_code=200,
                response_time=response_time,
                phone_number=phone_number,
            )

            return {
                "valid": True,
                "phone_number": phone_number_info.phone_number,
                "country_code": phone_number_info.country_code,
                "carrier": phone_number_info.carrier,
                "caller_name": phone_number_info.caller_name,
            }

        except TwilioException as e:
            self.logger.error(f"Twilio validation error: {e}")
            return {"valid": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"Phone validation error: {e}")
            return {"valid": False, "error": str(e)}


class PersonIdentificationEngine:
    """Main person identification engine"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(__name__)

        # Initialize components
        self.alpr_client = (
            OpenALPRClient(config.openalpr_secret_key)
            if config.openalpr_secret_key
            else None
        )
        self.vehicle_lookup = VehicleRegistrationLookup(config)
        self.neo4j_graph = Neo4jVehicleOwnerGraph(config)
        self.phone_validator = PhoneValidator(config)

    def identify_person_from_plate(
        self, plate: str, state: str = None
    ) -> Optional[PersonInfo]:
        """Identify person from license plate"""
        try:
            self.logger.info(f"Starting person identification for plate: {plate}")

            # Step 1: Lookup vehicle information
            vehicle_info = self.vehicle_lookup.lookup_vehicle_by_plate(plate, state)
            if not vehicle_info:
                self.logger.warning(f"No vehicle information found for plate: {plate}")
                return None

            # Step 2: Find owner using Neo4j graph
            person_info = self.neo4j_graph.find_owner_by_vehicle(plate, state)
            if person_info:
                self.logger.info(
                    f"Found person in Neo4j graph: {person_info.person_id}"
                )

                # Validate phone number if available
                if person_info.phone:
                    phone_validation = self.phone_validator.validate_phone(
                        person_info.phone
                    )
                    if not phone_validation.get("valid", False):
                        self.logger.warning(
                            f"Invalid phone number for person: {person_info.person_id}"
                        )
                        person_info.phone = None

                return person_info

            # Step 3: If no existing relationship, try to create one
            if vehicle_info.owner_id:
                # Create basic person info from vehicle registration
                person_info = PersonInfo(
                    person_id=vehicle_info.owner_id,
                    name="Unknown",  # Would need additional lookup
                    confidence_score=0.5,
                    sources=["vehicle_registration"],
                )

                # Store relationship in Neo4j for future use
                self.neo4j_graph.create_vehicle_owner_relationship(
                    vehicle_info, person_info, confidence=0.5
                )

                return person_info

            self.logger.warning(f"No owner information found for plate: {plate}")
            return None

        except Exception as e:
            self.logger.error(f"Error identifying person from plate: {e}")
            return None

    def identify_person_from_image(
        self, image_url: str, state: str = None
    ) -> List[PersonInfo]:
        """Identify person from traffic camera image"""
        if not self.alpr_client:
            self.logger.error("OpenALPR client not configured")
            return []

        try:
            # Step 1: Recognize license plates in image
            plates = self.alpr_client.recognize_plate(image_url, state)
            if not plates:
                self.logger.warning(f"No plates recognized in image: {image_url}")
                return []

            # Step 2: Identify persons for each recognized plate
            identified_persons = []

            for plate_info in plates:
                if plate_info["confidence"] < 80:  # Skip low-confidence plates
                    continue

                person = self.identify_person_from_plate(
                    plate_info["plate"], plate_info.get("region", state)
                )

                if person:
                    # Add plate recognition confidence to person info
                    person.confidence_score *= plate_info["confidence"] / 100
                    person.sources.append("license_plate_recognition")
                    identified_persons.append(person)

            return identified_persons

        except Exception as e:
            self.logger.error(f"Error identifying person from image: {e}")
            return []

    def process_accident_for_identification(self, accident_data: Dict) -> Dict:
        """Process accident data to identify involved persons"""
        try:
            result = {
                "accident_id": accident_data.get("id", ""),
                "identified_persons": [],
                "processing_timestamp": datetime.utcnow().isoformat(),
                "success": False,
            }

            # Look for license plates in accident description or metadata
            plates = self._extract_plates_from_text(
                accident_data.get("description", "")
            )

            # Look for traffic camera images
            images = accident_data.get("images", [])

            identified_persons = []

            # Process license plates
            for plate in plates:
                person = self.identify_person_from_plate(plate)
                if person:
                    identified_persons.append(person)

            # Process images
            for image_url in images:
                persons = self.identify_person_from_image(image_url)
                identified_persons.extend(persons)

            # Deduplicate persons
            unique_persons = self._deduplicate_persons(identified_persons)

            result["identified_persons"] = [
                {
                    "person_id": p.person_id,
                    "name": p.name,
                    "phone": p.phone,
                    "email": p.email,
                    "confidence_score": p.confidence_score,
                    "sources": p.sources,
                }
                for p in unique_persons
            ]

            result["success"] = len(unique_persons) > 0

            self.logger.log_data_processing(
                operation="person_identification",
                input_count=1,
                output_count=len(unique_persons),
                processing_time=0,
                accident_id=accident_data.get("id", ""),
                identified_count=len(unique_persons),
            )

            return result

        except Exception as e:
            self.logger.error(f"Error processing accident for identification: {e}")
            return {
                "accident_id": accident_data.get("id", ""),
                "identified_persons": [],
                "error": str(e),
                "success": False,
            }

    def _extract_plates_from_text(self, text: str) -> List[str]:
        """Extract license plate patterns from text"""
        import re

        # Common license plate patterns
        patterns = [
            r"\b[A-Z]{2,3}[0-9]{3,4}\b",  # ABC123, AB1234
            r"\b[0-9]{3}[A-Z]{3}\b",  # 123ABC
            r"\b[A-Z]{3}[0-9]{3}\b",  # ABC123
        ]

        plates = []
        for pattern in patterns:
            matches = re.findall(pattern, text.upper())
            plates.extend(matches)

        return list(set(plates))  # Remove duplicates

    def _deduplicate_persons(self, persons: List[PersonInfo]) -> List[PersonInfo]:
        """Remove duplicate persons based on person_id or phone"""
        seen_ids = set()
        seen_phones = set()
        unique_persons = []

        for person in persons:
            # Check by person_id
            if person.person_id and person.person_id in seen_ids:
                continue

            # Check by phone
            if person.phone and person.phone in seen_phones:
                continue

            unique_persons.append(person)

            if person.person_id:
                seen_ids.add(person.person_id)
            if person.phone:
                seen_phones.add(person.phone)

        return unique_persons

    def close(self):
        """Clean up resources"""
        if self.neo4j_graph:
            self.neo4j_graph.close()
