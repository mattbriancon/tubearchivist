# Config Store Tests

Comprehensive test suite for the pluggable datastore implementation.

## Test Structure

```
tests/
├── test_interfaces/
│   └── test_config_store_interface.py   # Interface contract tests
├── test_adapters/
│   ├── test_elasticsearch_config_store.py  # Elasticsearch adapter tests
│   └── test_model_config_store.py          # Model adapter tests
├── test_config_store_factory.py            # Factory tests
└── test_integration_config_usage.py        # Integration tests with AppConfig/UserConfig
```

## Running Tests

### Run all config store tests
```bash
pytest backend/common/tests/ -v
```

### Run specific test files
```bash
# Interface tests
pytest backend/common/tests/test_interfaces/test_config_store_interface.py -v

# Model adapter tests
pytest backend/common/tests/test_adapters/test_model_config_store.py -v

# Elasticsearch adapter tests
pytest backend/common/tests/test_adapters/test_elasticsearch_config_store.py -v

# Factory tests
pytest backend/common/tests/test_config_store_factory.py -v

# Integration tests
pytest backend/common/tests/test_integration_config_usage.py -v
```

### Run specific test classes
```bash
pytest backend/common/tests/test_adapters/test_model_config_store.py::TestModelConfigStoreBasicOperations -v
```

### Run specific test methods
```bash
pytest backend/common/tests/test_adapters/test_model_config_store.py::TestModelConfigStoreBasicOperations::test_set_and_get_new_config -v
```

### Run with coverage
```bash
pytest backend/common/tests/ --cov=backend/common/src --cov-report=html
```

## Test Coverage

### Interface Tests (`test_config_store_interface.py`)
- ✅ Interface is abstract and cannot be instantiated
- ✅ Interface defines all required methods
- ✅ ConfigNotFoundError exception works correctly
- ✅ Mock implementation adheres to contract

### Model Adapter Tests (`test_model_config_store.py`)
- ✅ Basic CRUD operations (get, set, delete)
- ✅ Update operations with deep merging
- ✅ List keys with prefix filtering
- ✅ Different data types (nested, unicode, empty)
- ✅ Error handling (not found, invalid JSON, non-serializable)

**Total: 27 tests**

### Elasticsearch Adapter Tests (`test_elasticsearch_config_store.py`)
- ✅ Basic CRUD operations with mocked ES
- ✅ Update operations
- ✅ Exists checks
- ✅ List keys with prefix filtering
- ✅ Error handling (404, 500, etc.)

**Total: 17 tests**

### Factory Tests (`test_config_store_factory.py`)
- ✅ Returns correct backend based on settings
- ✅ Handles backend aliases (sqlite -> model)
- ✅ Case insensitive
- ✅ Validates unsupported backends
- ✅ Returns new instances (no singleton)

**Total: 6 tests**

### Integration Tests (`test_integration_config_usage.py`)
- ✅ AppConfig initialization and updates
- ✅ UserConfig initialization and updates
- ✅ Default syncing
- ✅ Backend switching

**Total: 15 tests**

## Total Test Count

**65 tests** covering all aspects of the pluggable datastore implementation.

## Test Database

Tests marked with `@pytest.mark.django_db` use Django's test database, which is automatically created and torn down for each test. The ModelConfigStore tests use this feature to test against a real database (SQLite in test mode).

## Mocking

Elasticsearch adapter tests use `unittest.mock` to mock ElasticWrap responses, avoiding the need for a running Elasticsearch instance during tests.
