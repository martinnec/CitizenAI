"""
Simple example demonstrating basic usage of the Government Services Store.
"""

from government_services_store import GovernmentService, GovernmentServicesStore


def main():
    # Create a new store
    store = GovernmentServicesStore()
    
    # Create some example services
    services = [
        GovernmentService(
            uri="https://gov.example.com/services/driver-license",
            id="driver-license",
            name="Driver License Renewal",
            description="Renew your driver license online with quick digital verification"
        ),
        GovernmentService(
            uri="https://gov.example.com/services/voter-registration",
            id="voter-registration", 
            name="Voter Registration",
            description="Register to vote online for upcoming elections"
        ),
        GovernmentService(
            uri="https://gov.example.com/services/unemployment-benefits",
            id="unemployment-benefits",
            name="Unemployment Benefits Application",
            description="Apply for unemployment benefits with online document submission"
        )
    ]
    
    # Add services to the store
    store.add_services(services)
    print(f"Added {len(services)} services to the store")
    
    # Search for services related to "online"
    results = store.search_services_by_keywords(["online"], k=3)
    print(f"\nServices containing 'online' ({len(results)} found):")
    for service in results:
        print(f"- {service.name}")
    
    # Get a specific service
    service = store.get_service_by_id("driver-license")
    if service:
        print(f"\nDriver License Service Details:")
        print(f"Name: {service.name}")
        print(f"Description: {service.description}")
    
    # Show all services
    print(f"\nAll services in store ({store.get_services_count()} total):")
    for service in store.get_all_services():
        print(f"- {service.name} (ID: {service.id})")


if __name__ == "__main__":
    main()
