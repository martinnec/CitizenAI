"""
Comprehensive test suite for Government Services Store.

This file provides thorough testing of all GovernmentServicesStore functionality including:
- Service management (add, search, retrieve)
- Smart loading strategy with fallback
- Local storage and caching
- Automatic ID extraction from URIs
- Built-in Python operations
- Error handling scenarios
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
from unittest.mock import patch, MagicMock
from government_services_store import GovernmentService, GovernmentServicesStore


class TestGovernmentService(unittest.TestCase):
    """Test the GovernmentService dataclass."""
    
    def test_service_creation_with_explicit_id(self):
        """Test creating a service with explicit ID."""
        service = GovernmentService(
            uri="https://gov.example.com/services/test",
            id="test-service",
            name="Test Service",
            description="A test service",
            keywords=["test", "example"]
        )
        self.assertEqual(service.id, "test-service")
        self.assertEqual(service.name, "Test Service")
        self.assertEqual(service.keywords, ["test", "example"])
    
    def test_automatic_id_extraction_from_uri_path(self):
        """Test automatic ID extraction from URI path."""
        service = GovernmentService(
            uri="https://gov.example.com/services/passport-renewal",
            id="",
            name="Passport Service",
            description="Passport renewal service"
        )
        self.assertEqual(service.id, "passport-renewal")
        self.assertEqual(service.keywords, [])  # Should default to empty list
    
    def test_automatic_id_extraction_from_uri_fragment(self):
        """Test automatic ID extraction from URI fragment."""
        service = GovernmentService(
            uri="https://gov.example.com/services/licenses#business-license",
            id="",
            name="Business License",
            description="Business license application"
        )
        self.assertEqual(service.id, "business-license")
    
    def test_service_creation_fails_without_uri_or_id(self):
        """Test that service creation fails when both URI and ID are empty."""
        with self.assertRaises(ValueError):
            GovernmentService(
                uri="",
                id="",
                name="Invalid Service",
                description="This should fail"
            )
    
    def test_service_creation_fails_with_unparseable_uri(self):
        """Test service creation with URI that can't be parsed for ID."""
        with self.assertRaises(ValueError):
            GovernmentService(
                uri="https://gov.example.com/",
                id="",
                name="Invalid Service",
                description="URI has no extractable ID"
            )
    
    def test_service_creation_with_default_keywords(self):
        """Test creating a service with default empty keywords."""
        service = GovernmentService(
            uri="https://gov.example.com/services/test",
            id="test-service",
            name="Test Service",
            description="A test service"
            # keywords not specified, should default to empty list
        )
        self.assertEqual(service.keywords, [])
    
    def test_service_creation_with_none_keywords(self):
        """Test creating a service with None keywords (should become empty list)."""
        service = GovernmentService(
            uri="https://gov.example.com/services/test",
            id="test-service", 
            name="Test Service",
            description="A test service",
            keywords=None
        )
        self.assertEqual(service.keywords, [])


class TestGovernmentServicesStore(unittest.TestCase):
    """Test the GovernmentServicesStore class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.store = GovernmentServicesStore()
        self.sample_services = self.create_sample_services()
    
    def create_sample_services(self):
        """Create sample government services for testing."""
        return [
            GovernmentService(
                uri="https://gov.example.com/services/passport-renewal",
                id="passport-renewal",
                name="Passport Renewal Service",
                description="Online service for renewing expired or expiring passports. Submit documents digitally and track application status.",
                keywords=["passport", "renewal", "travel", "documents", "online"]
            ),
            GovernmentService(
                uri="https://gov.example.com/services/birth-certificate",
                id="birth-certificate",
                name="Birth Certificate Request",
                description="Request certified copies of birth certificates. Online digital application with secure document delivery options.",
                keywords=["birth", "certificate", "vital", "records", "identity"]
            ),
            GovernmentService(
                uri="https://gov.example.com/services/business-license",
                id="business-license",
                name="Business License Application",
                description="Apply for new business licenses online. Complete application process with digital document submission and approval tracking.",
                keywords=["business", "license", "permit", "commercial", "application"]
            ),
            GovernmentService(
                uri="https://gov.example.com/services/property-tax",
                id="property-tax",
                name="Property Tax Payment",
                description="Pay property taxes online with multiple payment options. View tax history and download receipts instantly.",
                keywords=["property", "tax", "payment", "real estate", "municipal"]
            ),
            GovernmentService(
                uri="https://gov.example.com/services/vehicle-registration",
                id="vehicle-registration",
                name="Vehicle Registration Renewal",
                description="Renew vehicle registration online. Upload insurance documents and receive digital registration confirmation.",
                keywords=["vehicle", "registration", "automotive", "DMV", "renewal"]
            )
        ]
    
    def test_add_single_service(self):
        """Test adding a single service to the store."""
        service = self.sample_services[0]
        self.store.add_service(service)
        
        self.assertEqual(len(self.store), 1)
        self.assertEqual(self.store.get_services_count(), 1)
        self.assertIn(service.id, self.store)
        
        retrieved = self.store.get_service_by_id(service.id)
        self.assertEqual(retrieved, service)
    
    def test_add_multiple_services(self):
        """Test adding multiple services to the store."""
        self.store.add_services(self.sample_services)
        
        self.assertEqual(len(self.store), len(self.sample_services))
        self.assertEqual(self.store.get_services_count(), len(self.sample_services))
        
        for service in self.sample_services:
            self.assertIn(service.id, self.store)
            retrieved = self.store.get_service_by_id(service.id)
            self.assertEqual(retrieved, service)
    
    def test_get_all_services(self):
        """Test retrieving all services from the store."""
        self.store.add_services(self.sample_services)
        
        all_services = self.store.get_all_services()
        self.assertEqual(len(all_services), len(self.sample_services))
        
        # Verify it's a copy, not the original list
        self.assertIsNot(all_services, self.store._services_list)
        
        # Verify all services are present
        service_ids = {service.id for service in all_services}
        expected_ids = {service.id for service in self.sample_services}
        self.assertEqual(service_ids, expected_ids)
    
    def test_get_service_by_id_existing(self):
        """Test retrieving an existing service by ID."""
        self.store.add_services(self.sample_services)
        service = self.store.get_service_by_id("passport-renewal")
        
        self.assertIsNotNone(service)
        self.assertEqual(service.id, "passport-renewal")
        self.assertEqual(service.name, "Passport Renewal Service")
    
    def test_get_service_by_id_nonexistent(self):
        """Test retrieving a non-existent service by ID."""
        self.store.add_services(self.sample_services)
        service = self.store.get_service_by_id("nonexistent-service")
        
        self.assertIsNone(service)
    
    def test_clear_store(self):
        """Test clearing all services from the store."""
        self.store.add_services(self.sample_services)
        self.assertEqual(len(self.store), len(self.sample_services))
        
        self.store.clear()
        self.assertEqual(len(self.store), 0)
        self.assertEqual(self.store.get_services_count(), 0)
        self.assertEqual(len(self.store.get_all_services()), 0)
    
    def test_python_built_in_len(self):
        """Test Python's built-in len() function."""
        self.assertEqual(len(self.store), 0)
        
        self.store.add_services(self.sample_services)
        self.assertEqual(len(self.store), len(self.sample_services))
    
    def test_python_built_in_contains(self):
        """Test Python's built-in 'in' operator."""
        self.store.add_services(self.sample_services)
        
        self.assertTrue("passport-renewal" in self.store)
        self.assertTrue("birth-certificate" in self.store)
        self.assertFalse("nonexistent-service" in self.store)
    
    def test_search_single_keyword(self):
        """Test searching with a single keyword."""
        self.store.add_services(self.sample_services)
        
        results = self.store.search_services_by_keywords(["online"], k=10)
        
        # All services should match since they all contain "online"
        self.assertEqual(len(results), len(self.sample_services))
        
        # Verify all results contain the keyword
        for service in results:
            service_keywords_text = " ".join(service.keywords) if service.keywords else ""
            searchable_text = f"{service.name} {service.description} {service_keywords_text}".lower()
            self.assertIn("online", searchable_text)
    
    def test_search_multiple_keywords(self):
        """Test searching with multiple keywords."""
        self.store.add_services(self.sample_services)
        
        results = self.store.search_services_by_keywords(["digital", "online"], k=10)
        
        # Should return services containing either keyword
        self.assertGreater(len(results), 0)
        
        # Verify results are ordered by keyword frequency
        for i in range(len(results) - 1):
            current_score = self._calculate_keyword_score(results[i], ["digital", "online"])
            next_score = self._calculate_keyword_score(results[i + 1], ["digital", "online"])
            self.assertGreaterEqual(current_score, next_score)
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        self.store.add_services(self.sample_services)
        
        lower_results = self.store.search_services_by_keywords(["online"])
        upper_results = self.store.search_services_by_keywords(["ONLINE"])
        mixed_results = self.store.search_services_by_keywords(["OnLiNe"])
        
        self.assertEqual(len(lower_results), len(upper_results))
        self.assertEqual(len(lower_results), len(mixed_results))
        
        # Results should be identical
        for i in range(len(lower_results)):
            self.assertEqual(lower_results[i].id, upper_results[i].id)
            self.assertEqual(lower_results[i].id, mixed_results[i].id)
    
    def test_search_no_keywords(self):
        """Test searching with empty keyword list."""
        self.store.add_services(self.sample_services)
        
        results = self.store.search_services_by_keywords([])
        self.assertEqual(len(results), 0)
        
        results = self.store.search_services_by_keywords(["", "  ", ""])
        self.assertEqual(len(results), 0)
    
    def test_search_no_matches(self):
        """Test searching with keywords that don't match any services."""
        self.store.add_services(self.sample_services)
        
        results = self.store.search_services_by_keywords(["spaceship", "alien"])
        self.assertEqual(len(results), 0)
    
    def test_search_top_k_limit(self):
        """Test that search respects the k parameter."""
        self.store.add_services(self.sample_services)
        
        results = self.store.search_services_by_keywords(["online"], k=3)
        self.assertLessEqual(len(results), 3)
        
        results = self.store.search_services_by_keywords(["online"], k=1)
        self.assertLessEqual(len(results), 1)
    
    def test_search_by_service_keywords(self):
        """Test searching using the keywords field of services."""
        self.store.add_services(self.sample_services)
        
        # Test search by specific keywords that are in the keywords field
        results = self.store.search_services_by_keywords(["passport"], k=10)
        self.assertGreater(len(results), 0)
        
        # The passport service should be included since "passport" is in its keywords
        passport_service = next((s for s in results if s.id == "passport-renewal"), None)
        self.assertIsNotNone(passport_service)
        
        # Test search by keyword that appears in keywords field but not name/description
        results = self.store.search_services_by_keywords(["travel"], k=10)
        self.assertGreater(len(results), 0)
        
        # Should find passport service due to "travel" keyword
        passport_service = next((s for s in results if s.id == "passport-renewal"), None)
        self.assertIsNotNone(passport_service)
        
        # Test search by multiple keywords including keywords field
        results = self.store.search_services_by_keywords(["DMV", "automotive"], k=10)
        self.assertGreater(len(results), 0)
        
        # Should find vehicle registration service
        vehicle_service = next((s for s in results if s.id == "vehicle-registration"), None)
        self.assertIsNotNone(vehicle_service)
    
    def _calculate_keyword_score(self, service, keywords):
        """Helper method to calculate keyword score for a service."""
        service_keywords_text = " ".join(service.keywords) if service.keywords else ""
        searchable_text = f"{service.name} {service.description} {service_keywords_text}".lower()
        score = 0
        for keyword in keywords:
            score += searchable_text.count(keyword.lower())
        return score


class TestGovernmentServicesStoreLocalStorage(unittest.TestCase):
    """Test local storage functionality of GovernmentServicesStore."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_data_path = Path("data/stores/government_services_store")
        self.test_data_path = Path(self.temp_dir) / "data/stores/government_services_store"
        self.test_data_path.mkdir(parents=True, exist_ok=True)
        
        self.store = GovernmentServicesStore()
        self.sample_services = [
            GovernmentService(
                uri="https://gov.example.com/services/test1",
                id="test1",
                name="Test Service 1",
                description="First test service",
                keywords=["test", "sample"]
            ),
            GovernmentService(
                uri="https://gov.example.com/services/test2",
                id="test2",
                name="Test Service 2",
                description="Second test service",
                keywords=["test", "example"]
            )
        ]
    
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_to_local_success(self):
        """Test successful storage to local JSON file."""
        # Create the expected directory structure in our temp dir
        json_file = self.test_data_path / "government_services_data.json"
        
        # Mock Path to return our test data path
        with patch('government_services_store.Path') as mock_path_constructor:
            # When Path("data/stores/government_services_store") is called, return our test path parent
            mock_path_constructor.return_value = self.test_data_path
            
            self.store.add_services(self.sample_services)
            
            # Store to local file
            self.store._store_to_local()
            
            # Verify file was created in our temp directory
            self.assertTrue(json_file.exists())
            
            # Verify file content
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.assertEqual(len(data), len(self.sample_services))
            
            for i, service_data in enumerate(data):
                self.assertEqual(service_data['id'], self.sample_services[i].id)
                self.assertEqual(service_data['name'], self.sample_services[i].name)
                self.assertEqual(service_data['uri'], self.sample_services[i].uri)
                self.assertEqual(service_data['description'], self.sample_services[i].description)
    
    def test_load_from_local_success(self):
        """Test successful loading from local JSON file."""
        # Create test JSON file
        json_file = self.test_data_path / "government_services_data.json"
        
        test_data = [
            {
                "uri": "https://gov.example.com/services/loaded1",
                "id": "loaded1",
                "name": "Loaded Service 1",
                "description": "First loaded service"
            },
            {
                "uri": "https://gov.example.com/services/loaded2",
                "id": "loaded2",
                "name": "Loaded Service 2",
                "description": "Second loaded service"
            }
        ]
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # Mock Path to return our test data path
        with patch('government_services_store.Path') as mock_path_constructor:
            # When Path("data/stores/government_services_store") is called, return our test path parent
            mock_path_constructor.return_value = self.test_data_path
            
            # Load from local file
            self.store._load_from_local()
            
            # Verify services were loaded
            self.assertEqual(self.store.get_services_count(), len(test_data))
            
            for service_data in test_data:
                service = self.store.get_service_by_id(service_data['id'])
                self.assertIsNotNone(service)
                self.assertEqual(service.name, service_data['name'])
                self.assertEqual(service.uri, service_data['uri'])
                self.assertEqual(service.description, service_data['description'])
    
    def test_load_from_local_file_not_found(self):
        """Test loading when local file doesn't exist."""
        # Point to non-existent file by using a different path
        with patch('government_services_store.Path') as mock_path_constructor:
            mock_path_constructor.return_value = Path("/nonexistent/path")
            
            with self.assertRaises(FileNotFoundError):
                self.store._load_from_local()
    
    def test_round_trip_storage(self):
        """Test storing and then loading data maintains integrity."""
        # Mock Path to return our test data path
        with patch('government_services_store.Path') as mock_path_constructor:
            mock_path_constructor.return_value = self.test_data_path
            
            # Add services and store
            self.store.add_services(self.sample_services)
            original_count = self.store.get_services_count()
            
            self.store._store_to_local()
            
            # Create new store and load
            new_store = GovernmentServicesStore()
            new_store._load_from_local()
            
            # Verify data integrity
            self.assertEqual(new_store.get_services_count(), original_count)
            
            for service in self.sample_services:
                loaded_service = new_store.get_service_by_id(service.id)
                self.assertIsNotNone(loaded_service)
                self.assertEqual(loaded_service.name, service.name)
                self.assertEqual(loaded_service.uri, service.uri)
                self.assertEqual(loaded_service.description, service.description)


class TestGovernmentServicesStoreLoadingStrategy(unittest.TestCase):
    """Test the smart loading strategy with fallback."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.store = GovernmentServicesStore()
    
    @patch('government_services_store.Path.exists')
    @patch.object(GovernmentServicesStore, '_load_from_local')
    def test_load_services_uses_local_when_available(self, mock_load_local, mock_exists):
        """Test that load_services uses local file when available."""
        mock_exists.return_value = True
        mock_load_local.return_value = None
        
        self.store.load_services()
        
        mock_load_local.assert_called_once()
    
    @patch('government_services_store.Path.exists')
    @patch.object(GovernmentServicesStore, '_load_from_external_store')
    def test_load_services_uses_external_when_local_unavailable(self, mock_load_external, mock_exists):
        """Test that load_services falls back to external when local is unavailable."""
        mock_exists.return_value = False
        mock_load_external.return_value = None
        
        self.store.load_services()
        
        mock_load_external.assert_called_once()
    
    @patch('government_services_store.Path.exists')
    @patch.object(GovernmentServicesStore, '_load_from_local')
    @patch.object(GovernmentServicesStore, '_load_from_external_store')
    def test_load_services_fallback_on_local_error(self, mock_load_external, mock_load_local, mock_exists):
        """Test that load_services falls back to external when local loading fails."""
        mock_exists.return_value = True
        mock_load_local.side_effect = Exception("Local loading failed")
        mock_load_external.return_value = None
        
        self.store.load_services()
        
        mock_load_local.assert_called_once()
        mock_load_external.assert_called_once()
    
    @patch('government_services_store.Path.exists')
    @patch.object(GovernmentServicesStore, '_load_from_external_store')
    def test_load_services_raises_error_when_both_fail(self, mock_load_external, mock_exists):
        """Test that load_services raises error when both local and external fail."""
        mock_exists.return_value = False
        mock_load_external.side_effect = Exception("External loading failed")
        
        with self.assertRaises(RuntimeError) as context:
            self.store.load_services()
        
        self.assertIn("Failed to load services from both local and external sources", str(context.exception))
    
    def test_load_services_clears_existing_data(self):
        """Test that load_services clears existing data before loading."""
        # Add some initial services
        initial_service = GovernmentService(
            uri="https://gov.example.com/services/initial",
            id="initial",
            name="Initial Service",
            description="Should be cleared"
        )
        self.store.add_service(initial_service)
        self.assertEqual(self.store.get_services_count(), 1)
        
        # Mock the loading to fail so we can check if clear was called
        with patch.object(self.store, '_load_from_external_store') as mock_external:
            with patch('government_services_store.Path.exists', return_value=False):
                mock_external.side_effect = Exception("Mock failure")
                
                try:
                    self.store.load_services()
                except RuntimeError:
                    pass  # Expected to fail
                
                # Services should have been cleared
                self.assertEqual(self.store.get_services_count(), 0)


def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("=" * 80)
    print("RUNNING COMPREHENSIVE GOVERNMENT SERVICES STORE TESTS")
    print("=" * 80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestGovernmentService,
        TestGovernmentServicesStore,
        TestGovernmentServicesStoreLocalStorage,
        TestGovernmentServicesStoreLoadingStrategy
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


# Legacy test function for backward compatibility
def test_government_services_store():
    """Legacy test function - now runs comprehensive tests."""
    return run_comprehensive_tests()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)
