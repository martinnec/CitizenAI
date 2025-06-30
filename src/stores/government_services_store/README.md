# CitizenAI Government Services Store

An in-memory store for managing government services specifications with search functionality.

## Features

- **Service Management**: Store and manage government services with URI, ID, name, and description
- **Keyword Search**: Search services by keywords with frequency-based ranking
- **Service Retrieval**: Get individual services by their ID
- **External Store Integration**: Placeholder for future external store connectivity

## Classes

### GovernmentService
A dataclass representing a government service with:
- `uri`: Linked Data identifier (required)
- `id`: Local application ID (auto-extracted from URI if not provided)
- `name`: Service name (required)
- `description`: Service description (required)

**Features:**
- Automatic ID extraction from URI using `urlparse()` if ID is empty
- Validation ensures ID is always available or raises `ValueError`
- ID is extracted as the last path segment or fragment from the URI

### GovernmentServicesStore
The main store class providing:

**Core Methods:**
- `load_services_from_external_store(external_store_url)`: Load services from external source (placeholder for future implementation)
- `search_services_by_keywords(keywords, k=10)`: Search top-K services by keywords with frequency-based ranking
- `get_service_by_id(service_id)`: Retrieve service by ID, returns `Optional[GovernmentService]`

**Service Management:**
- `add_service(service)`: Add a single service to the store
- `add_services(services)`: Add multiple services to the store
- `get_all_services()`: Get all services as a list copy
- `get_services_count()`: Get the number of services in the store
- `clear()`: Clear all services from the store

**Built-in Python Support:**
- `len(store)`: Get number of services using Python's `len()` function
- `service_id in store`: Check if service exists using Python's `in` operator

## Usage

```python
from government_services_store import GovernmentService, GovernmentServicesStore

# Create store
store = GovernmentServicesStore()

# Add services (ID auto-extracted from URI)
service = GovernmentService(
    uri="https://gov.example.com/services/passport-renewal",
    id="",  # Will be auto-extracted as "passport-renewal"
    name="Passport Renewal Service",
    description="Online service for renewing passports"
)
store.add_service(service)

# Add multiple services at once
services = [
    GovernmentService(
        uri="https://gov.example.com/services/driver-license",
        id="driver-license",
        name="Driver License Renewal",
        description="Renew driver license online"
    ),
    # ... more services
]
store.add_services(services)

# Search services (case-insensitive, frequency-ranked)
results = store.search_services_by_keywords(["online", "digital"], k=5)
for service in results:
    print(f"{service.name}: {service.description}")

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

## Search Algorithm

The `search_services_by_keywords()` method implements intelligent keyword matching:

1. **Case-insensitive matching**: All keywords are normalized to lowercase
2. **Frequency scoring**: Services are ranked by total keyword occurrences in name + description
3. **Regex-based matching**: Uses `re.escape()` for safe pattern matching
4. **Filtering**: Only returns services containing at least one keyword
5. **Sorting**: Results sorted by frequency (descending), then alphabetically by name
6. **Top-K results**: Returns up to K best matches (default: 10)

**Example:**
- Service: "Online Tax Filing - File taxes online with digital assistance" 
- Keywords: ["online", "digital"]
- Score: 2 (one "online" + one "digital")

## Dependencies

The implementation uses only Python standard library modules:
- `typing`: Type hints for better code quality
- `dataclasses`: For the `GovernmentService` dataclass
- `re`: Regular expressions for keyword matching
- `urllib.parse`: URI parsing for ID extraction
- `collections`: Not currently used but imported for future enhancements

## Testing

Run the test file to see the functionality in action:

```bash
cd scr
python test_government_services_store.py
```

The test file includes:
- Sample government services (passport, business license, tax filing, etc.)
- Keyword search demonstrations
- Service retrieval by ID
- Edge cases (no matches, empty searches)
- Automatic ID extraction examples

Run the simple example:
```bash
cd scr  
python example_usage.py
```

## Future Enhancements

- External store integration (REST API, database, etc.)
- Advanced search with fuzzy matching
- Service categorization and filtering
- Caching mechanisms
- Data persistence options
