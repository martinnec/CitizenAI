"""
Comprehensive example demonstrating all features of the Government Services Store.

This example covers:
- Smart loading with fallback strategy (local cache → external SPARQL)
- Service management (add, search, retrieve)
- Local storage and caching
- Automatic ID extraction from URIs
- Built-in Python operations
- Error handling scenarios
"""

from government_services_store import GovernmentService, GovernmentServicesStore
from pathlib import Path
import time


def demonstrate_loading_strategy():
    """Demonstrate the smart loading strategy with fallback."""
    print("=" * 60)
    print("1. SMART LOADING STRATEGY DEMONSTRATION")
    print("=" * 60)
    
    store = GovernmentServicesStore()
    
    print("Loading services using smart fallback strategy...")
    print("(Will try local cache first, then fallback to SPARQL endpoint)")
    
    try:
        start_time = time.time()
        store.load_services()
        load_time = time.time() - start_time
        
        print(f"✓ Successfully loaded {store.get_services_count()} services in {load_time:.2f} seconds")
        
        # Show first few services as examples
        if store.get_services_count() > 0:
            print("\nFirst 3 services loaded:")
            for i, service in enumerate(store.get_all_services()[:3]):
                print(f"  {i+1}. {service.name}")
                print(f"     ID: {service.id}")
                print(f"     URI: {service.uri}")
                print()
        
        return store
        
    except Exception as e:
        print(f"✗ Failed to load services: {e}")
        print("Continuing with manual service creation...")
        return store


def demonstrate_manual_service_creation(store):
    """Demonstrate manual service creation and management."""
    print("=" * 60)
    print("2. MANUAL SERVICE CREATION AND MANAGEMENT")
    print("=" * 60)
    
    # Clear store for manual demonstration
    store.clear()
    print("Cleared store for manual demonstration")
    
    # Create services with automatic ID extraction
    print("\nCreating services with automatic ID extraction from URIs...")
    services_with_auto_id = [
        GovernmentService(
            uri="https://gov.example.com/services/passport-renewal",
            id="",  # Will be auto-extracted as "passport-renewal"
            name="Passport Renewal Service",
            description="Renew your passport online with digital photo submission",
            keywords=["passport", "travel", "documents", "renewal", "identity"]
        ),
        GovernmentService(
            uri="https://gov.example.com/services/business-license#main",
            id="",  # Will be auto-extracted as "main"
            name="Business License Application",
            description="Apply for business license with online form submission",
            keywords=["business", "license", "permit", "commercial", "application"]
        )
    ]
    
    for service in services_with_auto_id:
        print(f"  URI: {service.uri} → ID: {service.id}")
    
    # Create services with explicit IDs
    manual_services = [
        GovernmentService(
            uri="https://gov.example.com/services/driver-license",
            id="driver-license",
            name="Driver License Renewal",
            description="Renew your driver license online with quick digital verification",
            keywords=["driver", "license", "DMV", "driving", "renewal", "verification"]
        ),
        GovernmentService(
            uri="https://gov.example.com/services/voter-registration",
            id="voter-registration", 
            name="Voter Registration",
            description="Register to vote online for upcoming elections",
            keywords=["voter", "voting", "election", "registration", "democracy", "civic"]
        ),
        GovernmentService(
            uri="https://gov.example.com/services/unemployment-benefits",
            id="unemployment-benefits",
            name="Unemployment Benefits Application",
            description="Apply for unemployment benefits with online document submission",
            keywords=["unemployment", "benefits", "social", "welfare", "assistance", "job"]
        ),
        GovernmentService(
            uri="https://gov.example.com/services/tax-filing",
            id="tax-filing",
            name="Online Tax Filing",
            description="File your taxes online with digital document upload and e-signature",
            keywords=["tax", "filing", "IRS", "income", "refund", "digital", "e-signature"]
        )
    ]
    
    # Add services to the store
    print(f"\nAdding {len(services_with_auto_id)} services with auto-extracted IDs...")
    store.add_services(services_with_auto_id)
    
    print(f"Adding {len(manual_services)} services with manual IDs...")
    store.add_services(manual_services)
    
    print(f"✓ Total services in store: {store.get_services_count()}")
    
    return store

def demonstrate_search_capabilities(store):
    """Demonstrate advanced search capabilities."""
    print("=" * 60)
    print("3. SEARCH CAPABILITIES DEMONSTRATION")
    print("=" * 60)
    
    # Single keyword search
    print("Searching for services containing 'online':")
    results = store.search_services_by_keywords(["online"], k=5)
    print(f"Found {len(results)} services:")
    for i, service in enumerate(results, 1):
        print(f"  {i}. {service.name}")
    
    # Multiple keyword search
    print("\nSearching for services containing 'digital' AND 'online':")
    results = store.search_services_by_keywords(["digital", "online"], k=3)
    print(f"Found {len(results)} services:")
    for i, service in enumerate(results, 1):
        print(f"  {i}. {service.name}")
        print(f"     Description: {service.description}")
    
    # Case-insensitive search
    print("\nCase-insensitive search for 'LICENSE' (uppercase):")
    results = store.search_services_by_keywords(["LICENSE"], k=3)
    print(f"Found {len(results)} services:")
    for service in results:
        print(f"  - {service.name}")
    
    # No results scenario
    print("\nSearching for non-existent keyword 'spaceship':")
    results = store.search_services_by_keywords(["spaceship"], k=5)
    print(f"Found {len(results)} services (should be 0)")
    
    # Empty search
    print("\nEmpty keyword search:")
    results = store.search_services_by_keywords([], k=5)
    print(f"Found {len(results)} services (should be 0)")


def demonstrate_keywords_search(store):
    """Demonstrate keyword-specific search capabilities."""
    print("=" * 60)
    print("4. KEYWORD-SPECIFIC SEARCH DEMONSTRATION")
    print("=" * 60)
    
    # Search by keywords that are in the keywords field
    print("Searching for services with keyword 'travel' (in keywords field):")
    results = store.search_services_by_keywords(["travel"], k=5)
    print(f"Found {len(results)} services:")
    for i, service in enumerate(results, 1):
        print(f"  {i}. {service.name}")
        print(f"     Keywords: {', '.join(service.keywords) if service.keywords else 'None'}")
    
    # Search by category-specific keywords
    print("\nSearching for services with keyword 'DMV':")
    results = store.search_services_by_keywords(["DMV"], k=5)
    print(f"Found {len(results)} services:")
    for service in results:
        print(f"  - {service.name}")
        print(f"    Keywords: {', '.join(service.keywords) if service.keywords else 'None'}")
    
    # Search combining keywords from different fields
    print("\nSearching for 'renewal' (appears in both name/description and keywords):")
    results = store.search_services_by_keywords(["renewal"], k=5)
    print(f"Found {len(results)} services:")
    for service in results:
        print(f"  - {service.name}")
        if service.keywords:
            keyword_match = "renewal" in [k.lower() for k in service.keywords]
            print(f"    Keywords contain 'renewal': {keyword_match}")
    
    # Search for civic/government-specific terms
    print("\nSearching for civic keywords 'democracy', 'civic':")
    results = store.search_services_by_keywords(["democracy", "civic"], k=5)
    print(f"Found {len(results)} services:")
    for service in results:
        print(f"  - {service.name}")
        print(f"    Matching keywords: {[k for k in service.keywords if k.lower() in ['democracy', 'civic']]}")


def demonstrate_service_retrieval(store):
    """Demonstrate individual service retrieval methods."""
    print("=" * 60)
    print("5. SERVICE RETRIEVAL DEMONSTRATION")
    print("=" * 60)
    
    # Get service by ID
    print("Retrieving service by ID 'driver-license':")
    service = store.get_service_by_id("driver-license")
    if service:
        print(f"✓ Found: {service.name}")
        print(f"  URI: {service.uri}")
        print(f"  Description: {service.description}")
    else:
        print("✗ Service not found")
    
    # Try to get non-existent service
    print("\nTrying to retrieve non-existent service 'unicorn-license':")
    service = store.get_service_by_id("unicorn-license")
    if service:
        print(f"✓ Found: {service.name}")
    else:
        print("✗ Service not found (expected)")
    
    # Get all services
    print(f"\nRetrieving all services:")
    all_services = store.get_all_services()
    print(f"Total services: {len(all_services)}")
    print("All service IDs:")
    for service in all_services:
        print(f"  - {service.id}: {service.name}")


def demonstrate_python_built_ins(store):
    """Demonstrate Python built-in operations."""
    print("=" * 60)
    print("6. PYTHON BUILT-IN OPERATIONS")
    print("=" * 60)
    
    # len() function
    print(f"Using len(store): {len(store)} services")
    print(f"Using store.get_services_count(): {store.get_services_count()} services")
    
    # in operator
    test_ids = ["driver-license", "nonexistent-service", "voter-registration"]
    print("\nUsing 'in' operator to check service existence:")
    for service_id in test_ids:
        exists = service_id in store
        print(f"  '{service_id}' in store: {exists}")


def demonstrate_local_storage(store):
    """Demonstrate local storage capabilities."""
    print("=" * 60)
    print("7. LOCAL STORAGE DEMONSTRATION")
    print("=" * 60)
    
    print("Storing current services to local JSON file...")
    try:
        # Use the private method directly for demonstration
        store._store_to_local()
        
        # Check if file was created
        local_file = Path("data/stores/government_services_store/government_services_data.json")
        if local_file.exists():
            file_size = local_file.stat().st_size
            print(f"✓ File created: {local_file}")
            print(f"  File size: {file_size} bytes")
        
        # Demonstrate loading from local file
        print("\nCreating new store and loading from local file...")
        new_store = GovernmentServicesStore()
        
        try:
            # Use the private method directly for demonstration
            new_store._load_from_local()
            print(f"✓ Loaded {new_store.get_services_count()} services from local file")
            
            # Verify data integrity
            if new_store.get_services_count() == store.get_services_count():
                print("✓ Data integrity verified - counts match")
            else:
                print("✗ Data integrity issue - counts don't match")
                
        except Exception as e:
            print(f"✗ Failed to load from local file: {e}")
        
    except Exception as e:
        print(f"✗ Failed to store to local file: {e}")


def demonstrate_error_handling():
    """Demonstrate error handling scenarios."""
    print("=" * 60)
    print("8. ERROR HANDLING DEMONSTRATION")
    print("=" * 60)
    
    # Invalid service creation
    print("Testing invalid service creation (no URI and no ID):")
    try:
        invalid_service = GovernmentService(
            uri="",
            id="",
            name="Invalid Service",
            description="This should fail"
        )
        print("✗ Should have failed but didn't")
    except ValueError as e:
        print(f"✓ Correctly caught error: {e}")
    
    # Service with missing ID but valid URI
    print("\nTesting service with empty ID but valid URI:")
    try:
        valid_service = GovernmentService(
            uri="https://example.com/services/test-service",
            id="",
            name="Test Service",
            description="Should work with auto-extracted ID"
        )
        print(f"✓ Successfully created service with auto-extracted ID: {valid_service.id}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def main():
    """Run comprehensive demonstration of all Government Services Store features."""
    print("GOVERNMENT SERVICES STORE - COMPREHENSIVE DEMONSTRATION")
    print("=" * 60)
    
    # 1. Demonstrate smart loading strategy
    store = demonstrate_loading_strategy()
    
    # 2. Demonstrate manual service creation and management
    store = demonstrate_manual_service_creation(store)
    
    # 3. Demonstrate search capabilities
    demonstrate_search_capabilities(store)
    
    # 4. Demonstrate keyword-specific search
    demonstrate_keywords_search(store)
    
    # 5. Demonstrate service retrieval
    demonstrate_service_retrieval(store)
    
    # 6. Demonstrate Python built-ins
    demonstrate_python_built_ins(store)
    
    # 7. Demonstrate local storage
    demonstrate_local_storage(store)
    
    # 8. Demonstrate error handling
    demonstrate_error_handling()
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    print(f"Final store contains {store.get_services_count()} services")


if __name__ == "__main__":
    main()
