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
            # Extract ID as the last part of the URI
            self.id = urlparse(self.uri).path.split('/')[-1] or urlparse(self.uri).fragment
        
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
    
    def load_services_from_external_store(self) -> None:
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
