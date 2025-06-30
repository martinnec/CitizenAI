"""
Government Services Store - An in-memory store for government service specifications.

This module provides a class to manage government services data with search functionality
and external store integration capabilities.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from collections import Counter
from urllib.parse import urlparse
from rdflib import Graph
import json
import os
from pathlib import Path

@dataclass
class GovernmentService:
    """Represents a government service with its specifications."""
    uri: str
    id: str
    name: str
    description: str
    
    def __post_init__(self):
        """Validate and extract ID from URI if not provided."""
        if not self.id and self.uri:
            parsed = urlparse(self.uri)
            # First try to extract from fragment
            if parsed.fragment:
                self.id = parsed.fragment
            # If no fragment, extract from path
            elif parsed.path:
                path_parts = [part for part in parsed.path.split('/') if part]
                if path_parts:
                    self.id = path_parts[-1]
        
        if not self.id:
            raise ValueError("Service ID could not be determined from URI")


class GovernmentServicesStore:
    """
    In-memory store for government services specifications.
    
    This class manages a collection of government services and provides
    functionality for loading, searching, and retrieving services.
    """
    
    def __init__(self):
        """Initialize an empty services store."""
        self._services: Dict[str, GovernmentService] = {}
        self._services_list: List[GovernmentService] = []
    
    def add_service(self, service: GovernmentService) -> None:
        """
        Add a service to the store.
        
        Args:
            service: The GovernmentService to add
        """
        self._services[service.id] = service
        self._services_list = list(self._services.values())
    
    def add_services(self, services: List[GovernmentService]) -> None:
        """
        Add multiple services to the store.
        
        Args:
            services: List of GovernmentService objects to add
        """
        for service in services:
            self._services[service.id] = service
        self._services_list = list(self._services.values())
    
    def search_services_by_keywords(self, keywords: List[str], k: int = 10) -> List[GovernmentService]:
        """
        Search for services containing keywords and return top-K results.
        
        Args:
            keywords: List of keywords to search for
            k: Number of top results to return (default: 10)
            
        Returns:
            List of top-K services ordered by keyword frequency in name and description
        """
        if not keywords:
            return []
        
        # Normalize keywords to lowercase for case-insensitive search
        normalized_keywords = [keyword.lower().strip() for keyword in keywords if keyword.strip()]
        
        if not normalized_keywords:
            return []
        
        service_scores = []
        
        for service in self._services_list:
            # Combine name and description for searching
            searchable_text = f"{service.name} {service.description}".lower()
            
            # Count keyword occurrences
            keyword_count = 0
            for keyword in normalized_keywords:
                # Use word boundaries to match whole words and partial matches
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                matches = pattern.findall(searchable_text)
                keyword_count += len(matches)
            
            # Only include services that contain at least one keyword
            if keyword_count > 0:
                service_scores.append((service, keyword_count))
        
        # Sort by keyword frequency (descending) and then by service name for consistency
        service_scores.sort(key=lambda x: (-x[1], x[0].name.lower()))
        
        # Return top-K services
        return [service for service, _ in service_scores[:k]]
    
    def get_service_by_id(self, service_id: str) -> Optional[GovernmentService]:
        """
        Get a service by its ID.
        
        Args:
            service_id: The ID of the service to retrieve
            
        Returns:
            The GovernmentService object if found, None otherwise
        """
        return self._services.get(service_id)
    
    def get_all_services(self) -> List[GovernmentService]:
        """
        Get all services in the store.
        
        Returns:
            List of all GovernmentService objects
        """
        return self._services_list.copy()
    
    def get_services_count(self) -> int:
        """
        Get the number of services in the store.
        
        Returns:
            Number of services in the store
        """
        return len(self._services)
    
    def clear(self) -> None:
        """Clear all services from the store."""
        self._services.clear()
        self._services_list.clear()
    
    def __len__(self) -> int:
        """Return the number of services in the store."""
        return len(self._services)
    
    def __contains__(self, service_id: str) -> bool:
        """Check if a service with the given ID exists in the store."""
        return service_id in self._services
    
    def load_services(self) -> None:
        """
        Load services using a fallback strategy.
        
        Algorithm:
        1) If the current list of services is non-empty, clear it
        2) If the local file exists, load from local file
        3) Otherwise, load from external SPARQL store
        
        Raises:
            RuntimeError: If both local and external loading fail
            FileNotFoundError: If local file doesn't exist and external loading fails
        """
        # Step 1: Clear existing services if any
        if len(self._services) > 0:
            self.clear()
        
        # Step 2: Try to load from local file first
        local_file_path = Path("data/stores/government_services_store/government_services_data.json")
        
        if local_file_path.exists():
            try:
                self._load_from_local()
                return
            except Exception as local_error:
                print(f"Warning: Failed to load from local file: {local_error}")
                # Clear any partially loaded data before trying external store
                self.clear()
        
        # Step 3: If local file doesn't exist or loading failed, load from external store
        try:
            self._load_from_external_store()
        except Exception as external_error:
            raise RuntimeError(f"Failed to load services from both local and external sources. "
                             f"External error: {external_error}")
    
    def _load_from_external_store(self) -> None:
        """
        Load services from an external SPARQL store.
        
        This method queries the Czech government open data SPARQL endpoint
        to load government services and populate the in-memory store.
        
        Raises:
            RuntimeError: If the SPARQL query fails or data cannot be loaded
        """
        sparql_endpoint = "https://rpp-opendata.egon.gov.cz/odrpp/sparql/"

        g = Graph()

        sparql_str = f"""
        PREFIX rppl: <https://slovník.gov.cz/legislativní/sbírka/111/2009/pojem/>
        PREFIX rppa: <https://slovník.gov.cz/agendový/104/pojem/>
        SELECT ?uri ?name ?description
        WHERE {{
            SERVICE <{sparql_endpoint}> {{
            ?uri a rppl:služba-veřejné-správy ;
                rppa:má-název-služby ?name ;
                rppa:má-popis-služby ?description .
            }}
        }}
        """

        try:
            # Clear existing services before loading new ones
            self.clear()
            
            # Execute SPARQL query
            results = g.query(sparql_str)
            
            # Process results and create GovernmentService objects
            loaded_services = []
            for row in results:
                try:
                    # Extract values from SPARQL result row
                    uri = str(row.uri) if row.uri else ""
                    name = str(row.name) if row.name else ""
                    description = str(row.description) if row.description else ""
                    
                    # Skip services with missing essential data
                    if not uri or not name:
                        continue
                    
                    # Create GovernmentService object (ID will be auto-extracted from URI)
                    service = GovernmentService(
                        uri=uri,
                        id="",  # Will be auto-extracted from URI in __post_init__
                        name=name,
                        description=description
                    )
                    
                    loaded_services.append(service)
                    
                except Exception as service_error:
                    # Log individual service creation errors but continue processing
                    print(f"Warning: Failed to create service from row {row}: {service_error}")
                    continue
            
            # Add all successfully created services to the store
            if loaded_services:
                self.add_services(loaded_services)
                print(f"Successfully loaded {len(loaded_services)} services from external SPARQL store")
            else:
                print("No services were loaded from the external store")
                
        except Exception as e:
            raise RuntimeError(f"Failed to load services from external store: {e}")
    
    def _store_to_local(self) -> None:
        """
        Store all services to a local JSON file.
        
        Serializes the current services in the store to a JSON file at:
        data/stores/government_services_store/government_services_data.json
        
        Raises:
            RuntimeError: If the file cannot be written or directory creation fails
        """
        try:
            # Define the output file path
            output_dir = Path("data/stores/government_services_store")
            output_file = output_dir / "government_services_data.json"
            
            # Create directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert services to serializable format
            services_data = []
            for service in self._services_list:
                service_dict = {
                    "uri": service.uri,
                    "id": service.id,
                    "name": service.name,
                    "description": service.description
                }
                services_data.append(service_dict)
            
            # Write to JSON file with proper formatting
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(services_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully stored {len(services_data)} services to {output_file}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to store services to local file: {e}")
    
    def _load_from_local(self) -> None:
        """
        Load services from a local JSON file.
        
        Loads services from the JSON file at:
        data/stores/government_services_store/government_services_data.json
        
        Raises:
            RuntimeError: If the file cannot be read or parsed
            FileNotFoundError: If the JSON file doesn't exist
        """
        try:
            # Define the input file path
            input_dir = Path("data/stores/government_services_store")
            input_file = input_dir / "government_services_data.json"
            
            # Check if file exists
            if not input_file.exists():
                raise FileNotFoundError(f"Services data file not found: {input_file}")
            
            # Clear existing services before loading new ones
            self.clear()
            
            # Read and parse JSON file
            with open(input_file, 'r', encoding='utf-8') as f:
                services_data = json.load(f)
            
            # Convert JSON data back to GovernmentService objects
            loaded_services = []
            for service_dict in services_data:
                try:
                    # Validate required fields
                    if not all(key in service_dict for key in ['uri', 'id', 'name', 'description']):
                        print(f"Warning: Skipping service with missing fields: {service_dict}")
                        continue
                    
                    # Create GovernmentService object
                    service = GovernmentService(
                        uri=service_dict['uri'],
                        id=service_dict['id'],
                        name=service_dict['name'],
                        description=service_dict['description']
                    )
                    
                    loaded_services.append(service)
                    
                except Exception as service_error:
                    # Log individual service creation errors but continue processing
                    print(f"Warning: Failed to create service from data {service_dict}: {service_error}")
                    continue
            
            # Add all successfully created services to the store
            if loaded_services:
                self.add_services(loaded_services)
                print(f"Successfully loaded {len(loaded_services)} services from local file")
            else:
                print("No services were loaded from the local file")
                
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load services from local file: {e}")
