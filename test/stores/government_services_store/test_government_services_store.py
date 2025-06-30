"""
Test file for Government Services Store.

This file demonstrates the usage of the GovernmentServicesStore class
and provides example services for testing.
"""

from src.stores.government_services_store import GovernmentService, GovernmentServicesStore


def create_sample_services():
    """Create sample government services for testing."""
    services = [
        GovernmentService(
            uri="https://gov.example.com/services/passport-renewal",
            id="passport-renewal",
            name="Passport Renewal Service",
            description="Online service for renewing expired or expiring passports. Submit documents digitally and track application status."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/birth-certificate",
            id="birth-certificate",
            name="Birth Certificate Request",
            description="Request certified copies of birth certificates. Digital application with secure document delivery options."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/business-license",
            id="business-license",
            name="Business License Application",
            description="Apply for new business licenses online. Complete application process with digital document submission and approval tracking."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/property-tax",
            id="property-tax",
            name="Property Tax Payment",
            description="Pay property taxes online with multiple payment options. View tax history and download receipts instantly."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/vehicle-registration",
            id="vehicle-registration",
            name="Vehicle Registration Renewal",
            description="Renew vehicle registration online. Upload insurance documents and receive digital registration confirmation."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/marriage-license",
            id="marriage-license",
            name="Marriage License Application",
            description="Apply for marriage license online. Schedule appointments and submit required documentation digitally."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/tax-filing",
            id="tax-filing",
            name="Online Tax Filing",
            description="File annual tax returns online with guided assistance. Digital document upload and secure submission process."
        ),
        GovernmentService(
            uri="https://gov.example.com/services/building-permit",
            id="building-permit",
            name="Building Permit Application",
            description="Apply for construction and renovation permits. Submit architectural plans digitally and track approval status."
        )
    ]
    return services


def test_government_services_store():
    """Test the GovernmentServicesStore functionality."""
    print("=== Testing Government Services Store ===\n")
    
    # Create store and add sample services
    store = GovernmentServicesStore()
    sample_services = create_sample_services()
    store.add_services(sample_services)
    
    print(f"Added {store.get_services_count()} services to the store.\n")
    
    # Test 1: Search by keywords
    print("1. Testing keyword search:")
    print("-" * 40)
    
    keywords = ["online", "digital"]
    results = store.search_services_by_keywords(keywords, k=5)
    print(f"Searching for keywords: {keywords}")
    print(f"Found {len(results)} services:")
    for i, service in enumerate(results, 1):
        print(f"  {i}. {service.name} (ID: {service.id})")
        print(f"     Description: {service.description[:80]}...")
    print()
    
    # Test 2: Search for specific service type
    print("2. Testing specific keyword search:")
    print("-" * 40)
    
    keywords = ["license"]
    results = store.search_services_by_keywords(keywords, k=3)
    print(f"Searching for keywords: {keywords}")
    print(f"Found {len(results)} services:")
    for i, service in enumerate(results, 1):
        print(f"  {i}. {service.name} (ID: {service.id})")
    print()
    
    # Test 3: Get service by ID
    print("3. Testing get service by ID:")
    print("-" * 40)
    
    service_id = "passport-renewal"
    service = store.get_service_by_id(service_id)
    if service:
        print(f"Found service with ID '{service_id}':")
        print(f"  Name: {service.name}")
        print(f"  URI: {service.uri}")
        print(f"  Description: {service.description}")
    else:
        print(f"Service with ID '{service_id}' not found.")
    print()
    
    # Test 4: Search with no results
    print("4. Testing search with no matching keywords:")
    print("-" * 40)
    
    keywords = ["spaceship", "alien"]
    results = store.search_services_by_keywords(keywords, k=5)
    print(f"Searching for keywords: {keywords}")
    print(f"Found {len(results)} services")
    print()
    
    # Test 5: Get all services
    print("5. Testing get all services:")
    print("-" * 40)
    
    all_services = store.get_all_services()
    print(f"Total services in store: {len(all_services)}")
    for service in all_services:
        print(f"  - {service.name} (ID: {service.id})")
    print()
    
    # Test 6: Test service creation with URI parsing
    print("6. Testing automatic ID extraction from URI:")
    print("-" * 40)
    
    test_service = GovernmentService(
        uri="https://gov.example.com/services/test-service-123",
        id="",  # Empty ID to test automatic extraction
        name="Test Service",
        description="A test service for URI parsing"
    )
    print(f"URI: {test_service.uri}")
    print(f"Extracted ID: {test_service.id}")
    print()


if __name__ == "__main__":
    test_government_services_store()
