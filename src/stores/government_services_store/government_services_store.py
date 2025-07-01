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
import openai
import chromadb
from chromadb.config import Settings
import hashlib

@dataclass
class GovernmentService:
    """Represents a government service with its specifications."""
    uri: str
    id: str
    name: str
    description: str
    keywords: List[str] = None
    
    def __post_init__(self):
        """Validate and extract ID from URI if not provided."""
        # Initialize keywords as empty list if None
        if self.keywords is None:
            self.keywords = []
            
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
        
        # Semantic search components
        self._openai_client = None
        self._chroma_client = None
        self._collection = None
        self._embeddings_computed = False
    
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
            List of top-K services ordered by keyword frequency in name, description, and keywords
        """
        print(f"[DEBUG] search_services_by_keywords called with keywords={keywords}, k={k}")
        if not keywords:
            print("[DEBUG] No keywords provided. Returning empty list.")
            return []
        
        # Normalize keywords to lowercase for case-insensitive search
        normalized_keywords = [keyword.lower().strip() for keyword in keywords if keyword.strip()]
        
        if not normalized_keywords:
            print("[DEBUG] No valid normalized keywords after processing. Returning empty list.")
            return []
        
        service_scores = []
        
        for service in self._services_list:
            # Combine name, description, and keywords for searching
            service_keywords_text = " ".join(service.keywords) if service.keywords else ""
            searchable_text = f"{service.name} {service.description} {service_keywords_text}".lower()
            
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
        
        found_count = len(service_scores[:k])
        print(f"[DEBUG] search_services_by_keywords finished. Number of services found: {found_count}")
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
        """Clear all services from the store and reset semantic search state."""
        self._services.clear()
        self._services_list.clear()
        self._embeddings_computed = False
        
        # Clear ChromaDB collection if it exists
        if self._collection:
            try:
                # Delete all embeddings from the collection
                existing_data = self._collection.get()
                if existing_data['ids']:
                    self._collection.delete(ids=existing_data['ids'])
                print("[DEBUG] Cleared embeddings from ChromaDB collection.")
            except Exception as e:
                print(f"[DEBUG] Warning: Failed to clear ChromaDB collection: {e}")
    
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
        3) Otherwise, load from external SPARQL store and compute embeddings
        
        Note: Embeddings are only computed when loading from external store,
        not when loading from local cache for performance reasons.
        
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
            except Exception as local_error:
                print(f"[DEBUG] Warning: Failed to load from local file: {local_error}")
                # Clear any partially loaded data before trying external store
                self.clear()
        
        # Step 3: If local file doesn't exist or loading failed, load from external store
        if len(self._services) == 0:
            try:
                self._load_from_external_store()
                self._load_auxiliary_details()
                
                # Compute embeddings for semantic search (only when loading from external store)
                try:
                    print("[DEBUG] Computing embeddings for semantic search...")
                    self._compute_embeddings()
                except Exception as embedding_error:
                    print(f"[DEBUG] Warning: Failed to compute embeddings: {embedding_error}")
                    print("[DEBUG] Semantic search will not be available until embeddings are computed manually.")
                    
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
                    
                    # Create GovernmentService object (ID will be auto-extracted from URI in __post_init__
                    service = GovernmentService(
                        uri=uri,
                        id="",  # Will be auto-extracted from URI in __post_init__
                        name=name,
                        description=description,
                        keywords=[]  # Default to empty keywords list
                    )
                    
                    loaded_services.append(service)
                    
                except Exception as service_error:
                    # Log individual service creation errors but continue processing
                    print(f"[DEBUG] Warning: Failed to create service from row {row}: {service_error}")
                    continue
            
            # Add all successfully created services to the store
            if loaded_services:
                self.add_services(loaded_services)
                print(f"[DEBUG] Successfully loaded {len(loaded_services)} services from external SPARQL store")
            else:
                print("[DEBUG] No services were loaded from the external store")
                
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
                    "description": service.description,
                    "keywords": service.keywords if service.keywords else []
                }
                services_data.append(service_dict)
            
            # Write to JSON file with proper formatting
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(services_data, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG] Successfully stored {len(services_data)} services to {output_file}")
            
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
                        print(f"[DEBUG] Warning: Skipping service with missing fields: {service_dict}")
                        continue
                    
                    # Get keywords if present, otherwise default to empty list
                    keywords = service_dict.get('keywords', [])
                    
                    # Create GovernmentService object
                    service = GovernmentService(
                        uri=service_dict['uri'],
                        id=service_dict['id'],
                        name=service_dict['name'],
                        description=service_dict['description'],
                        keywords=keywords
                    )
                    
                    loaded_services.append(service)
                    
                except Exception as service_error:
                    # Log individual service creation errors but continue processing
                    print(f"[DEBUG] Warning: Failed to create service from data {service_dict}: {service_error}")
                    continue
            
            # Add all successfully created services to the store
            if loaded_services:
                self.add_services(loaded_services)
                print(f"[DEBUG] Successfully loaded {len(loaded_services)} services from local file")
            else:
                print("[DEBUG] No services were loaded from the local file")
                
        except FileNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to load services from local file: {e}")

    def _load_auxiliary_details(self) -> None:
        """
        Load auxiliary details from a local JSON file and merge them with existing services.
        """
        details_file_path = Path("data/stores/government_services_store/government_services_details.json")
        if not details_file_path.exists():
            print(f"[DEBUG] Warning: Auxiliary details file not found at {details_file_path}")
            return

        try:
            with open(details_file_path, 'r', encoding='utf-8') as f:
                details_data = json.load(f)

            if "položky" not in details_data:
                print("[DEBUG] Warning: 'položky' key not found in auxiliary details file.")
                return

            details_map = {item['kód']: item for item in details_data["položky"] if 'kód' in item}

            for service in self._services_list:
                if service.id in details_map:
                    details = details_map[service.id]
                    
                    # Append description
                    if 'popis' in details and 'cs' in details['popis'] and details['popis']['cs']:
                        # Remove HTML tags before appending
                        clean_description = re.sub(r'<[^>]+>', '', details['popis']['cs'])
                        service.description += " " + clean_description
                    
                    # Append keywords
                    if 'klíčová-slova' in details and isinstance(details['klíčová-slova'], list):
                        for keyword_item in details['klíčová-slova']:
                            if 'cs' in keyword_item and keyword_item['cs']:
                                service.keywords.append(keyword_item['cs'])
            
            print("[DEBUG] Successfully loaded and merged auxiliary details.")

        except json.JSONDecodeError:
            print(f"[DEBUG] Warning: Could not decode JSON from {details_file_path}")
        except Exception as e:
            print(f"[DEBUG] An error occurred while loading auxiliary details: {e}")

    def get_service_detail_by_id(self, service_id: str) -> Optional[str]:
        """
        Return additional details about the serivce as a string for the service with the given ID from
        data/stores/government_services_store/government_services_details.json.
        Args:
            service_id: The ID of the service to retrieve details for.
        Returns:
            A string with the service detail if found, otherwise None.
        """
        details_file_path = Path("data/stores/government_services_store/government_services_details.json")
        if not details_file_path.exists():
            print(f"[DEBUG] Details file not found at {details_file_path}")
            return None
        try:
            with open(details_file_path, 'r', encoding='utf-8') as f:
                details_data = json.load(f)
            if "položky" not in details_data:
                print("[DEBUG] 'položky' key not found in details file.")
                return None
            for item in details_data["položky"]:
                if item.get("kód") == service_id:
                    # Helper function to safely get nested value
                    def safe_get_cs(key):
                        if key in item and item[key] and isinstance(item[key], dict) and 'cs' in item[key] and item[key]['cs']:
                            return self._remove_html_tags(item[key]['cs'])
                        return "Není k dispozici"
                    
                    # Build output string with safe access to all keys
                    output_parts = []
                    
                    benefit = safe_get_cs('jaký-má-služba-benefit')
                    output_parts.append(f"Přínos: {benefit}")
                    
                    faq = safe_get_cs('časté-dotazy')
                    output_parts.append(f"Časté dotazy: {faq}")
                    
                    target_group = safe_get_cs('týká-se-vás-to-pokud')
                    output_parts.append(f"Pro koho je služba určena: {target_group}")
                    
                    # Electronic processing - combine two fields if both exist
                    electronic_where = safe_get_cs('kde-a-jak-službu-řešit-el')
                    electronic_how = safe_get_cs('způsob-vyřízení-el')
                    if electronic_where != "Není k dispozici" or electronic_how != "Není k dispozici":
                        electronic_combined = f"{electronic_where} {electronic_how}".strip()
                        if electronic_combined != "Není k dispozici Není k dispozici":
                            output_parts.append(f"Kde a jak službu řešit elektronicky: {electronic_combined}")
                    
                    # Personal processing - combine two fields if both exist
                    personal_where = safe_get_cs('kde-a-jak-službu-řešit-os')
                    personal_how = safe_get_cs('způsob-vyřízení-os')
                    if personal_where != "Není k dispozici" or personal_how != "Není k dispozici":
                        personal_combined = f"{personal_where} {personal_how}".strip()
                        if personal_combined != "Není k dispozici Není k dispozici":
                            output_parts.append(f"Kde a jak službu řešit osobně: {personal_combined}")
                    
                    when_to_handle = safe_get_cs('kdy-službu-řešit')
                    output_parts.append(f"Kdy službu řešit: {when_to_handle}")
                    
                    service_output = safe_get_cs('výstup-služby')
                    output_parts.append(f"Co je výstupem nebo výsledkem služby: {service_output}")
                    
                    output_str = "\n                    ".join(output_parts)
                    print(f"[DEBUG] Service with id {service_id} has detailed description and it was successfully retrieved.")
                    return output_str
            print(f"[DEBUG] Service with id {service_id} not found in details file.")
            return None
        except Exception as e:
            print(f"[DEBUG] Error reading details file: {e}")
            return None
        
    def get_service_howto_by_id(self, service_id: str) -> Optional[str]:
        """
        Return how to handle the service electronically for the service with the given ID from
        data/stores/government_services_store/government_services_details.json.
        
        Args:
            service_id: The ID of the service to retrieve electronic handling info for.
            
        Returns:
            A string with electronic handling instructions if found, otherwise None.
        """
        details_file_path = Path("data/stores/government_services_store/government_services_details.json")
        if not details_file_path.exists():
            print(f"[DEBUG] Details file not found at {details_file_path}")
            return None
        
        try:
            with open(details_file_path, 'r', encoding='utf-8') as f:
                details_data = json.load(f)
            
            if "položky" not in details_data:
                print("[DEBUG] 'položky' key not found in details file.")
                return None
            
            for item in details_data["položky"]:
                if item.get("kód") == service_id:
                    # Helper function to safely get nested value
                    def safe_get_cs(key):
                        if key in item and item[key] and isinstance(item[key], dict) and 'cs' in item[key] and item[key]['cs']:
                            return self._remove_html_tags(item[key]['cs'])
                        return None
                    
                    # Get electronic processing fields
                    electronic_where = safe_get_cs('kde-a-jak-službu-řešit-el')
                    electronic_how = safe_get_cs('způsob-vyřízení-el')
                    
                    # Combine the fields if they exist
                    if electronic_where or electronic_how:
                        parts = []
                        if electronic_where:
                            parts.append(electronic_where)
                        if electronic_how:
                            parts.append(electronic_how)
                        
                        combined = "Kde a jak službu řešit elektronicky: " + " ".join(parts).strip()
                        if combined:
                            print(f"[DEBUG] Service with id {service_id} has electronic handling info which was successfully retrieved.")
                            return combined
                    
                    print(f"[DEBUG] Service with id {service_id} has no electronic handling information.")
                    return None
            
            print(f"[DEBUG] Service with id {service_id} not found in details file.")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error reading details file: {e}")
            return None

    def _remove_html_tags(self, text: str) -> str:
        """
        Remove HTML tags from a string.
        
        Args:
            text: The input string potentially containing HTML tags
            
        Returns:
            The input string with HTML tags removed
        """
        return re.sub(r'<[^>]+>', '', text) if text else text
    
    def _initialize_semantic_search(self) -> None:
        """
        Initialize the OpenAI client and ChromaDB for semantic search.
        
        Raises:
            RuntimeError: If OpenAI API key is not set or initialization fails
        """
        try:
            # Initialize OpenAI client
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY environment variable is not set")
            
            self._openai_client = openai.OpenAI(api_key=api_key)
            
            # Initialize ChromaDB with persistent storage
            persist_directory = Path("data/stores/government_services_store/chromadb")
            persist_directory.mkdir(parents=True, exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(
                path=str(persist_directory)
            )
            
            # Get or create collection for government services
            self._collection = self._chroma_client.get_or_create_collection(
                name="government_services",
                metadata={"description": "Government services embeddings for semantic search"}
            )
            
            print(f"[DEBUG] Semantic search initialized. Collection has {self._collection.count()} embeddings.")
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize semantic search: {e}")
    
    def _get_service_text_for_embedding(self, service: GovernmentService) -> str:
        """
        Get the concatenated text representation of a service for embedding.
        
        Args:
            service: The GovernmentService object
            
        Returns:
            Concatenated string of name, description, and keywords
        """
        keywords_text = " ".join(service.keywords) if service.keywords else ""
        return f"{service.name} {service.description} {keywords_text}".strip()
    
    def _compute_embeddings(self) -> None:
        """
        Compute embeddings for all services and store them in ChromaDB with persistence.
        
        This method:
        1. Initializes semantic search components if not already done
        2. Computes embeddings for all services using OpenAI text-embedding-3-large
        3. Processes services in batches of 500 to avoid token-per-minute limits
        4. Stores embeddings in ChromaDB with service metadata
        5. Handles incremental updates (only computes embeddings for new services)
        
        Raises:
            RuntimeError: If OpenAI API key is not set or embedding computation fails
        """
        if not self._services_list:
            print("[DEBUG] No services to compute embeddings for.")
            return
        
        # Initialize semantic search components if not already done
        if not self._openai_client or not self._collection:
            self._initialize_semantic_search()
        
        try:
            # Get existing service IDs in the collection to avoid recomputing
            existing_ids = set()
            try:
                existing_data = self._collection.get()
                existing_ids = set(existing_data['ids']) if existing_data['ids'] else set()
            except Exception:
                # Collection might be empty or not exist yet
                pass
            
            # Filter services that need embeddings computed
            services_to_embed = [
                service for service in self._services_list 
                if service.id not in existing_ids
            ]
            
            if not services_to_embed:
                print("[DEBUG] All services already have embeddings computed.")
                self._embeddings_computed = True
                return
            
            print(f"[DEBUG] Computing embeddings for {len(services_to_embed)} services...")
            
            # Process services in batches of 500 to avoid token limits
            batch_size = 500
            total_processed = 0
            
            for i in range(0, len(services_to_embed), batch_size):
                batch_services = services_to_embed[i:i + batch_size]
                batch_number = (i // batch_size) + 1
                total_batches = (len(services_to_embed) + batch_size - 1) // batch_size
                
                print(f"[DEBUG] Processing batch {batch_number}/{total_batches} ({len(batch_services)} services)...")
                
                # Prepare data for this batch
                service_texts = []
                service_ids = []
                service_metadata = []
                
                for service in batch_services:
                    text = self._get_service_text_for_embedding(service)
                    service_texts.append(text)
                    service_ids.append(service.id)
                    service_metadata.append({
                        "name": service.name,
                        "uri": service.uri,
                        "description": service.description[:500],  # Limit description length for metadata
                        "keywords_count": len(service.keywords) if service.keywords else 0
                    })
                
                # Compute embeddings for this batch using OpenAI API
                embeddings_response = self._openai_client.embeddings.create(
                    input=service_texts,
                    model="text-embedding-3-large"
                )
                
                # Extract embeddings from response
                embeddings = [embedding.embedding for embedding in embeddings_response.data]
                
                # Store embeddings for this batch in ChromaDB
                self._collection.add(
                    embeddings=embeddings,
                    documents=service_texts,
                    ids=service_ids,
                    metadatas=service_metadata
                )
                
                total_processed += len(batch_services)
                print(f"[DEBUG] Batch {batch_number}/{total_batches} completed. Total processed: {total_processed}/{len(services_to_embed)}")
            
            self._embeddings_computed = True
            print(f"[DEBUG] Successfully computed and stored embeddings for {len(services_to_embed)} services.")
            print(f"[DEBUG] Total embeddings in collection: {self._collection.count()}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to compute embeddings: {e}")
    
    def search_services_semantically(self, query: str, k: int = 10) -> List[GovernmentService]:
        """
        Search for services semantically similar to the input query.
        
        Args:
            query: Input string describing a life situation or service need
            k: Number of top results to return (default: 10)
            
        Returns:
            List of top-K most semantically similar services
            
        Raises:
            RuntimeError: If embeddings haven't been computed or search fails
        """
        print(f"[DEBUG] search_services_semantically called with query='{query}', k={k}")
        
        if not query.strip():
            print("[DEBUG] Empty query provided. Returning empty list.")
            return []
        
        # Initialize semantic search components if not already done
        if not self._openai_client or not self._collection:
            self._initialize_semantic_search()
        
        # Ensure embeddings are computed
        if not self._embeddings_computed or self._collection.count() == 0:
            print("[DEBUG] Embeddings not computed yet. Computing embeddings first...")
            self._compute_embeddings()
        
        try:
            # Compute embedding for the query
            query_embedding_response = self._openai_client.embeddings.create(
                input=[query],
                model="text-embedding-3-large"
            )
            query_embedding = query_embedding_response.data[0].embedding
            
            # Search for similar services in ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, self._collection.count())
            )
            
            # Extract service IDs from results
            if not results['ids'] or not results['ids'][0]:
                print("[DEBUG] No semantic search results found.")
                return []
            
            service_ids = results['ids'][0]
            distances = results['distances'][0] if results['distances'] else []
            
            # Get corresponding services from the store
            matching_services = []
            for i, service_id in enumerate(service_ids):
                service = self.get_service_by_id(service_id)
                if service:
                    matching_services.append(service)
                    if distances:
                        print(f"[DEBUG] Found service '{service.name}' with distance {distances[i]:.4f}")
            
            print(f"[DEBUG] search_services_semantically finished. Found {len(matching_services)} services.")
            return matching_services
            
        except Exception as e:
            raise RuntimeError(f"Failed to perform semantic search: {e}")
    
    def get_service_steps_by_id(self, service_id: str) -> List[str]:
        """
        Retrieve the list of steps for a service using SPARQL query.
        
        Args:
            service_id: The ID of the service to retrieve steps for
            
        Returns:
            List of strings, each representing a step in format "step_name: step_description"
            
        Raises:
            RuntimeError: If the SPARQL query fails
        """
        if not service_id:
            return []
        
        sparql_endpoint = "https://rpp-opendata.egon.gov.cz/odrpp/sparql/"
        
        sparql_str = f"""
        PREFIX rppl: <https://slovník.gov.cz/legislativní/sbírka/111/2009/pojem/>
        PREFIX rppa: <https://slovník.gov.cz/agendový/104/pojem/>
        SELECT ?step ?name ?description
        WHERE {{
          SERVICE <{sparql_endpoint}> {{
            <https://rpp-opendata.egon.gov.cz/odrpp/zdroj/služba/{service_id}> rppa:skládá-se-z-úkonu ?step .
            
            ?step rppa:je-digitální true .
            
            ?step rppa:má-název-úkonu-služby ?name ;
                  rppa:má-popis-úkonu-služby ?description ;
                  rppa:je-realizován-kanálem/rppa:má-typ-obslužného-kanálu <https://rpp-opendata.egon.gov.cz/odrpp/zdroj/typ-obslužného-kanálu/DATOVA_SCHRANKA>
          }}
        }}
        ORDER BY ?step
        """
        
        try:
            g = Graph()
            results = g.query(sparql_str)
            
            steps = []
            for row in results:
                try:
                    name = str(row.name) if row.name else ""
                    description = str(row.description) if row.description else ""
                    
                    # Skip steps with missing essential data
                    if not name:
                        continue
                    
                    # Format as "name: description"
                    if description:
                        step_text = f"{name}: {description}"
                    else:
                        step_text = name
                    
                    steps.append(step_text)
                    
                except Exception as step_error:
                    print(f"[DEBUG] Warning: Failed to process step from row {row}: {step_error}")
                    continue
            
            print(f"[DEBUG] Successfully retrieved {len(steps)} steps for service {service_id}")
            return steps
            
        except Exception as e:
            raise RuntimeError(f"[DEBUG] Failed to retrieve steps for service {service_id}: {e}")

    def get_embedding_statistics(self) -> Dict[str, any]:
        """
        Get statistics about the current embeddings in the store.
        
        Returns:
            Dictionary with embedding statistics
        """
        if not self._collection:
            try:
                self._initialize_semantic_search()
            except Exception:
                return {
                    "embeddings_computed": False,
                    "total_embeddings": 0,
                    "total_services": len(self._services_list),
                    "coverage_percentage": 0.0
                }
        
        total_embeddings = self._collection.count()
        total_services = len(self._services_list)
        coverage = (total_embeddings / total_services * 100) if total_services > 0 else 0
        
        return {
            "embeddings_computed": self._embeddings_computed,
            "total_embeddings": total_embeddings,
            "total_services": total_services,
            "coverage_percentage": round(coverage, 2)
        }

