#!/usr/bin/env python3
"""
Alternative script to load government services and ensure they are stored locally.

This script:
1. Creates a GovernmentServicesStore instance
2. Uses the load_services() method (which tries local first, then external)
3. Ensures the services are stored locally for future use

Usage:
    python load_services_simple.py
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path to import our store
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from stores.government_services_store.government_services_store import GovernmentServicesStore


def main():
    """Main function to load government services and ensure local storage."""
    print("Loading government services...")
    
    try:
        # Create a new GovernmentServicesStore instance
        store = GovernmentServicesStore()
        
        # Load services using the fallback strategy (local first, then external)
        print("Loading services (will try local file first, then external SPARQL if needed)...")
        store.load_services()
        
        # Check how many services were loaded
        services_count = store.get_services_count()
        print(f"Loaded {services_count} services")
        
        if services_count == 0:
            print("Warning: No services were loaded.")
            return
        
        # Ensure services are stored locally (in case they were loaded from external)
        local_file_path = Path("data/stores/government_services_store/government_services_data.json")
        if not local_file_path.exists():
            print("Local file doesn't exist, storing services locally...")
            store._store_to_local()
        else:
            print("Local file already exists, services are available locally.")
        
        # Display summary
        print(f"\n📊 Summary:")
        print(f"   Total services loaded: {services_count}")
        print(f"   Local storage: {local_file_path}")
        
        # Show a few sample services
        print(f"\n🔍 Sample services:")
        all_services = store.get_all_services()
        for i, service in enumerate(all_services[:2]):  # Show first 2 services
            print(f"   • {service.name}")
            if len(service.description) > 80:
                print(f"     {service.description[:80]}...")
            else:
                print(f"     {service.description}")
        
        print(f"\n✅ Government services are ready for use!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
