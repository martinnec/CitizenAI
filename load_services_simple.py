#!/usr/bin/env python3
"""
Alternative script to load government services and ensure they are stored locally.

This script:
1. Creates a GovernmentServicesStore instance
2. Uses the load_services() method (which tries local first, then external)
3. Ensures the services are stored locally for future use
4. Reports on semantic search capabilities and embedding status
5. Demonstrates semantic search if embeddings are available

Usage:
    python load_services_simple.py
    
    # To enable semantic search (embeddings computed when loading from external store):
    set OPENAI_API_KEY=your-api-key-here
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
        
        # Check embedding status
        embedding_stats = store.get_embedding_statistics()
        print(f"\n🧠 Semantic Search Status:")
        print(f"   Embeddings computed: {'✅ Yes' if embedding_stats['embeddings_computed'] else '❌ No'}")
        print(f"   Total embeddings: {embedding_stats['total_embeddings']}")
        print(f"   Coverage: {embedding_stats['coverage_percentage']}% ({embedding_stats['total_embeddings']}/{embedding_stats['total_services']} services)")
        
        if not embedding_stats['embeddings_computed'] or embedding_stats['total_embeddings'] == 0:
            print(f"   💡 Tip: Set OPENAI_API_KEY environment variable to enable semantic search")
            print(f"        Embeddings are computed when loading from external store")
        else:
            print(f"   🎯 Semantic search is available!")
        
        # Show a few sample services
        print(f"\n🔍 Sample services:")
        all_services = store.get_all_services()
        for i, service in enumerate(all_services[:2]):  # Show first 2 services
            print(f"   • {service.name}")
            if len(service.description) > 80:
                print(f"     {service.description[:80]}...")
            else:
                print(f"     {service.description}")
        
        # Demonstrate search capabilities if embeddings are available
        if embedding_stats['embeddings_computed'] and embedding_stats['total_embeddings'] > 0:
            print(f"\n🔍 Testing semantic search...")
            try:
                # Test semantic search with a simple query
                test_query = "I need to register my newborn baby"
                semantic_results = store.search_services_semantically(test_query, k=2)
                
                if semantic_results:
                    print(f"   Query: '{test_query}'")
                    print(f"   Found {len(semantic_results)} relevant services:")
                    for i, service in enumerate(semantic_results, 1):
                        print(f"     {i}. {service.name}")
                else:
                    print(f"   No results found for test query")
            except Exception as search_error:
                print(f"   ⚠️  Semantic search test failed: {search_error}")
        
        print(f"\n✅ Government services are ready for use!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
