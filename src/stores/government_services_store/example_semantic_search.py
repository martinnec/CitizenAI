"""
Example usage of semantic search functionality in GovernmentServicesStore.

This example demonstrates how to use the new semantic search features.
"""

import os
from government_services_store import GovernmentServicesStore

def main():
    """Example usage of semantic search functionality."""
    
    # Set up OpenAI API key (you need to set this environment variable)
    # os.environ['OPENAI_API_KEY'] = 'your-openai-api-key-here'
    
    # Check if API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Please set the OPENAI_API_KEY environment variable to use semantic search.")
        print("You can set it by running: $env:OPENAI_API_KEY='your-api-key' (PowerShell)")
        return
    
    # Initialize the store
    print("Initializing Government Services Store...")
    store = GovernmentServicesStore()
    
    try:
        # Load services from external store or local file
        print("Loading services...")
        store.load_services()
        
        print(f"Loaded {store.get_services_count()} services.")
        
        # Get embedding statistics
        stats = store.get_embedding_statistics()
        print(f"Embedding statistics: {stats}")
        
        # Example semantic searches
        test_queries = [
            "I need to register my newborn baby",
            "I want to start a new business",
            "I need help with unemployment benefits",
            "I need to register my car",
            "I want to get married",
            "I need to renew my passport",
            "I want to apply for social housing",
            "I need medical care for elderly parent"
        ]
        
        print("\n" + "="*60)
        print("SEMANTIC SEARCH EXAMPLES")
        print("="*60)
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 50)
            
            try:
                # Perform semantic search
                results = store.search_services_semantically(query, k=3)
                
                if results:
                    for i, service in enumerate(results, 1):
                        print(f"{i}. {service.name}")
                        print(f"   Description: {service.description[:100]}...")
                        if service.keywords:
                            print(f"   Keywords: {', '.join(service.keywords[:3])}...")
                        print()
                else:
                    print("No services found for this query.")
            except Exception as e:
                print(f"Error performing semantic search: {e}")
        
        # Compare with keyword search
        print("\n" + "="*60)
        print("COMPARISON: SEMANTIC vs KEYWORD SEARCH")
        print("="*60)
        
        test_query = "I need to register my newborn baby"
        print(f"\nTest query: '{test_query}'")
        
        print("\nSemantic Search Results:")
        semantic_results = store.search_services_semantically(test_query, k=5)
        for i, service in enumerate(semantic_results, 1):
            print(f"{i}. {service.name}")
        
        print("\nKeyword Search Results (using words: baby, newborn, register):")
        keyword_results = store.search_services_by_keywords(["baby", "newborn", "register"], k=5)
        for i, service in enumerate(keyword_results, 1):
            print(f"{i}. {service.name}")
        
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()
