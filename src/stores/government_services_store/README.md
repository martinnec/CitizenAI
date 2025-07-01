# CitizenAI Government Services Store

An in-memory store for managing government services specifications with search functionality and data persistence.

## Features

- **Service Management**: Store and manage government services with URI, ID, name, description, and keywords
- **Semantic Search**: AI-powered search using OpenAI embeddings and ChromaDB vector database
- **Keyword Search**: Search services by keywords with frequency-based ranking across all fields
- **Service Retrieval**: Get individual services by their ID
- **External Store Integration**: Load services from Czech government SPARQL endpoint
- **Local Data Persistence**: Cache services locally as JSON for faster subsequent loads
- **Fallback Loading Strategy**: Automatically falls back from local to external data sources

## Classes

### GovernmentService
A dataclass representing a government service with:
- `uri`: Linked Data identifier (required)
- `id`: Local application ID (auto-extracted from URI if not provided)
- `name`: Service name (required)
- `description`: Service description (required)
- `keywords`: List of keywords characterizing the service (optional, defaults to empty list)

**Features:**
- Automatic ID extraction from URI using `urlparse()` if ID is empty
- Validation ensures ID is always available or raises `ValueError`
- Smart ID extraction: prioritizes URI fragment, then falls back to last path segment
- Supports both path-based URIs (`/services/passport-renewal`) and fragment-based URIs (`/services#passport-renewal`)
- **Keywords initialization**: Automatically initializes `keywords` as empty list if `None` is provided

**Keywords Field:**
The `keywords` field is a `List[str]` that allows you to:
- Categorize services with relevant terms (e.g., ["passport", "travel", "documents"])
- Improve search discoverability with domain-specific terminology
- Support multilingual or synonym-based search enhancement
- Default to empty list if not provided or set to `None`

### GovernmentServicesStore
The main store class providing:

**Data Loading:**
- `load_services()`: Smart loading with fallback strategy (local file → external SPARQL endpoint)

**Core Methods:**
- `search_services_by_keywords(keywords, k=10)`: Search top-K services by keywords with frequency-based ranking across name, description, and keywords fields
- `search_services_semantically(query, k=10)`: AI-powered semantic search using vector embeddings to find services matching a natural language query describing a life situation
- `get_service_by_id(service_id)`: Retrieve service by ID, returns `Optional[GovernmentService]`

**Semantic Search Methods:**
- `_compute_embeddings()`: Compute and store vector embeddings for all services using OpenAI text-embedding-3-large model
- `get_embedding_statistics()`: Get statistics about computed embeddings and coverage
- `_initialize_semantic_search()`: Initialize OpenAI client and ChromaDB components

**Service Management:**
- `add_service(service)`: Add a single service to the store
- `add_services(services)`: Add multiple services to the store
- `get_all_services()`: Get all services as a list copy
- `get_services_count()`: Get the number of services in the store
- `clear()`: Clear all services from the store

**Built-in Python Support:**
- `len(store)`: Get number of services using Python's `len()` function
- `service_id in store`: Check if service exists using Python's `in` operator

**Data Persistence:**
- `_store_to_local()`: Store services to local JSON file (internal method)
- `_load_from_local()`: Load services from local JSON file (internal method)
- `_load_from_external_store()`: Load services from SPARQL endpoint (internal method)

## Data Sources

### Local JSON Cache
Services are cached locally at `data/stores/government_services_store/government_services_data.json` for faster loading.

### External SPARQL Endpoint
The store integrates with the Czech government open data SPARQL endpoint:
- **Endpoint**: `https://rpp-opendata.egon.gov.cz/odrpp/sparql/`
- **Query**: Retrieves government services (`služba-veřejné-správy`) with names and descriptions
- **Automatic Fallback**: Used when local cache is unavailable or corrupted

## Usage

```python
from government_services_store import GovernmentService, GovernmentServicesStore

# Create store
store = GovernmentServicesStore()

# Load services using smart fallback strategy
# Will load from local cache if available, otherwise from SPARQL endpoint
store.load_services()

# Add custom services (ID auto-extracted from URI)
service = GovernmentService(
    uri="https://gov.example.com/services/passport-renewal",
    id="",  # Will be auto-extracted as "passport-renewal"
    name="Passport Renewal Service",
    description="Online service for renewing passports",
    keywords=["passport", "travel", "documents", "renewal", "identity"]
)
store.add_service(service)

# Add multiple services at once
services = [
    GovernmentService(
        uri="https://gov.example.com/services/driver-license",
        id="driver-license",
        name="Driver License Renewal",
        description="Renew driver license online",
        keywords=["driver", "license", "DMV", "driving", "renewal"]
    ),
    # ... more services
]
store.add_services(services)

# Search services (case-insensitive, frequency-ranked across all fields)
results = store.search_services_by_keywords(["online", "digital"], k=5)
for service in results:
    print(f"{service.name}: {service.description}")
    print(f"Keywords: {', '.join(service.keywords)}")

# Search by specific keywords
travel_services = store.search_services_by_keywords(["travel"], k=3)
dmv_services = store.search_services_by_keywords(["DMV"], k=3)

# Get service by ID
service = store.get_service_by_id("passport-renewal")
if service:
    print(f"Found: {service.name}")

# Use Python built-ins
print(f"Store has {len(store)} services")
if "passport-renewal" in store:
    print("Passport service is available")

# Get all services
all_services = store.get_all_services()
print(f"Total services: {store.get_services_count()}")
```

## Loading Strategy

The `load_services()` method implements a smart fallback strategy:

1. **Clear existing data** if the store is not empty
2. **Try local cache first**: Load from `data/stores/government_services_store/government_services_data.json`
3. **Fallback to external**: If local file doesn't exist or fails, query the SPARQL endpoint
4. **Error handling**: Provides detailed error messages and graceful degradation

**Benefits:**
- **Fast startup**: Local cache loads instantly
- **Always up-to-date**: Falls back to live data when cache is unavailable
- **Robust**: Handles network failures and file corruption gracefully

## Search Algorithm

The `search_services_by_keywords()` method implements intelligent keyword matching:

1. **Case-insensitive matching**: All keywords are normalized to lowercase
2. **Multi-field search**: Searches across service name, description, and keywords fields
3. **Frequency scoring**: Services are ranked by total keyword occurrences in all searchable fields
4. **Regex-based matching**: Uses `re.escape()` for safe pattern matching
5. **Filtering**: Only returns services containing at least one keyword
6. **Sorting**: Results sorted by frequency (descending), then alphabetically by name
7. **Top-K results**: Returns up to K best matches (default: 10)

**Search Fields:**
- Service name
- Service description  
- Service keywords (list of strings)

**Example:**
- Service: "Online Tax Filing" with description "File taxes online with digital assistance" and keywords ["tax", "IRS", "digital"]
- Keywords: ["online", "digital"] 
- Score: 3 (one "online" in description + one "digital" in description + one "digital" in keywords)

## Semantic Search

The store supports AI-powered semantic search using OpenAI embeddings and ChromaDB vector database. This allows you to search for services using natural language descriptions of life situations.

### Setup

1. **Install dependencies**:
```bash
pip install openai chromadb numpy
```

2. **Set OpenAI API key**:
```bash
# PowerShell
$env:OPENAI_API_KEY = "your-openai-api-key-here"

# Command Prompt
set OPENAI_API_KEY=your-openai-api-key-here

# Linux/Mac
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Usage

```python
import os
from government_services_store import GovernmentServicesStore

# Ensure API key is set
os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'

# Create store and load services
store = GovernmentServicesStore()
store.load_services()  # Automatically computes embeddings after loading

# Semantic search with natural language queries
results = store.search_services_semantically("I need to register my newborn baby", k=3)
for service in results:
    print(f"• {service.name}")
    print(f"  {service.description}")

# More examples
business_services = store.search_services_semantically("I want to start a small business", k=5)
unemployment_help = store.search_services_semantically("I lost my job and need financial help", k=3)
marriage_services = store.search_services_semantically("I want to get married", k=2)

# Check embedding statistics
stats = store.get_embedding_statistics()
print(f"Embeddings computed: {stats['embeddings_computed']}")
print(f"Coverage: {stats['coverage_percentage']}% ({stats['total_embeddings']}/{stats['total_services']})")
```

### How It Works

1. **Text Concatenation**: For each service, the system concatenates the name, description, and keywords into a single text
2. **Embedding Generation**: Uses OpenAI's `text-embedding-3-large` model to generate vector embeddings
3. **Vector Storage**: Stores embeddings in ChromaDB with persistent storage at `data/stores/government_services_store/chromadb`
4. **Query Processing**: When searching, the query is embedded using the same model
5. **Similarity Search**: ChromaDB finds the most similar services using vector similarity (cosine distance)
6. **Results Ranking**: Returns top-K most semantically similar services

### Benefits of Semantic Search

- **Natural Language**: Search using everyday language descriptions of life situations
- **Context Understanding**: Finds relevant services even without exact keyword matches
- **Intelligent Matching**: Understands relationships between concepts (e.g., "newborn" relates to "birth registration")
- **Multilingual Potential**: Can work across languages with appropriate embeddings
- **Persistent Storage**: Embeddings are cached locally for fast subsequent searches

### Comparison: Keyword vs Semantic Search

```python
# Keyword search - requires exact or partial word matches
keyword_results = store.search_services_by_keywords(["baby", "birth"], k=3)

# Semantic search - understands meaning and context
semantic_results = store.search_services_semantically("I just had a baby and need to register them", k=3)

# Semantic search often finds more relevant results for complex queries
complex_query = "My elderly parent needs medical assistance and I don't know where to start"
relevant_services = store.search_services_semantically(complex_query, k=5)
```

## Dependencies

The implementation requires the following packages:

**Standard Library**: `typing`, `dataclasses`, `re`, `urllib.parse`, `json`, `pathlib`, `os`, `hashlib`

**External Libraries**: 
- `rdflib>=6.0.0`: For SPARQL query execution and RDF graph processing
- `openai>=1.0.0`: For generating vector embeddings using OpenAI API (semantic search)
- `chromadb>=0.4.0`: For storing and querying vector embeddings (semantic search)
- `numpy>=1.24.0`: For numerical operations with vectors (semantic search)

### Installation

**Basic functionality** (keyword search, data loading):
```bash
pip install rdflib
```

**Full functionality** (including semantic search):
```bash
pip install rdflib openai chromadb numpy
```

**From requirements.txt**:
```
rdflib>=6.0.0
openai>=1.0.0
chromadb>=0.4.0
numpy>=1.24.0
```

## Testing

Run the comprehensive test suite to see all functionality in action:

```bash
cd src/stores/government_services_store
python test_government_services_store.py
```

The test suite now includes **35+ comprehensive tests** covering:

**GovernmentService Tests:**
- Service creation with explicit IDs
- Automatic ID extraction from URI paths and fragments
- Error handling for invalid service creation
- Validation of unparseable URIs

**GovernmentServicesStore Core Tests:**
- Adding single and multiple services
- Service retrieval by ID (existing and non-existent)
- Getting all services with proper data isolation
- Store clearing functionality
- Python built-in operations (`len()`, `in` operator)

**Advanced Search Tests:**
- Single and multiple keyword searches
- Case-insensitive search functionality
- Frequency-based ranking verification
- Empty keyword handling

**Semantic Search Tests:**
- Semantic search initialization and configuration
- OpenAI API integration testing
- ChromaDB vector storage testing
- Query embedding and similarity search
- Text extraction for embedding
- Embedding statistics and coverage reporting
- Error handling for missing API keys
- Empty query handling

**Local Storage Tests:**
- Storing services to JSON files
- Loading services from JSON files
- Round-trip data integrity verification
- File not found error handling
- Data persistence across store instances

**Smart Loading Strategy Tests:**
- Local file priority when available
- Fallback to external SPARQL endpoint
- Error handling when local loading fails
- Proper error reporting when both sources fail
- Data clearing before loading

**Test Results:**
- ✅ 28 tests run
- ✅ 100% success rate
- ✅ Comprehensive error handling coverage
- ✅ Mock-based testing for external dependencies

Run the comprehensive example demonstration:
```bash
cd src/stores/government_services_store
python example_usage_government_services_store.py
```

This example demonstrates:
- Smart loading with fallback strategy
- Manual service creation with automatic ID extraction
- Advanced search capabilities with multiple scenarios
- Service retrieval methods
- Python built-in operations
- Local storage functionality
- Error handling scenarios

## File Structure

```
src/stores/government_services_store/
├── __init__.py
├── government_services_store.py      # Main implementation
├── test_government_services_store.py # Comprehensive test suite (28 tests)
├── example_usage_government_services_store.py # Comprehensive usage examples
└── README.md                         # This file

data/stores/government_services_store/
└── government_services_data.json     # Local cache (auto-created)
```

## Implementation Details

**Method Naming Convention:**
- Public methods: `load_services()`, `search_services_by_keywords()`, `search_services_semantically()`, etc.
- Internal methods: `_store_to_local()`, `_load_from_local()`, `_load_from_external_store()`, `_compute_embeddings()`, `_initialize_semantic_search()`
- Private attributes: `_services`, `_services_list`

**Error Handling:**
- `ValueError`: Raised when service ID cannot be determined from URI
- `FileNotFoundError`: Raised when local JSON file doesn't exist
- `RuntimeError`: Raised when both local and external loading fail
- Graceful degradation with detailed error messages

**Data Validation:**
- Required fields validation for JSON loading
- URI parsing with fallback mechanisms
- Individual service creation error handling
- Data integrity verification in tests

## Future Enhancements

- **Advanced search**: Fuzzy matching and semantic search capabilities
- **Service categorization**: Organize services by government departments or topics
- **Caching mechanisms**: Intelligent cache invalidation and refresh strategies
- **Data validation**: Enhanced validation for government service data
- **Multi-language support**: Support for services in multiple languages
- **API integration**: REST API wrapper for web service integration
- **Performance optimization**: Indexing and query optimization for large datasets
- **Async support**: Asynchronous loading from external endpoints
- **Data export**: Export services to various formats (CSV, XML, etc.)
- **Service versioning**: Track changes and versions of government services
