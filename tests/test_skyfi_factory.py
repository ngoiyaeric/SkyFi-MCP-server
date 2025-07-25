"""
Tests for SkyFi Client Factory

Test suite for the collective intelligence client factory implementation
including credential caching, connection pooling, and thread safety.
"""

import asyncio
import pytest
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from mcp_skyfi.skyfi.factory import (
    SkyFiClientFactory,
    CredentialCacheEntry,
    ConnectionPool,
    get_client_factory,
    create_skyfi_client
)
from mcp_skyfi.skyfi.config import SkyFiConfig
from mcp_skyfi.skyfi.client import SkyFiClient
from mcp_skyfi.exceptions import SkyFiAuthenticationError, SkyFiAPIError


class TestCredentialCacheEntry:
    """Test credential cache entry functionality."""
    
    def test_create_valid_entry(self):
        """Test creating valid credential cache entry."""
        entry = CredentialCacheEntry(
            credential="test-key-123",
            auth_type="api_key",
            is_valid=True,
            user_info={"email": "test@example.com"}
        )
        
        assert entry.credential == "test-key-123"
        assert entry.auth_type == "api_key"
        assert entry.is_valid is True
        assert entry.user_info["email"] == "test@example.com"
        assert entry.validation_count == 1
        assert entry.error_message is None
    
    def test_create_invalid_entry(self):
        """Test creating invalid credential cache entry."""
        entry = CredentialCacheEntry(
            credential="invalid-key",
            auth_type="api_key",
            is_valid=False,
            error_message="Invalid API key"
        )
        
        assert entry.is_valid is False
        assert entry.error_message == "Invalid API key"
        assert entry.user_info == {}
    
    def test_refresh_validation(self):
        """Test refreshing validation status."""
        entry = CredentialCacheEntry(
            credential="test-key",
            auth_type="api_key",
            is_valid=False,
            error_message="Initial error"
        )
        
        initial_time = entry.last_validated
        time.sleep(0.01)  # Small delay
        
        entry.refresh_validation(
            is_valid=True,
            user_info={"email": "test@example.com"}
        )
        
        assert entry.is_valid is True
        assert entry.user_info["email"] == "test@example.com"
        assert entry.error_message is None
        assert entry.validation_count == 2
        assert entry.last_validated > initial_time
    
    def test_to_dict(self):
        """Test converting entry to dictionary."""
        entry = CredentialCacheEntry(
            credential="test-key",
            auth_type="oauth",
            is_valid=True,
            user_info={"email": "test@example.com"}
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["auth_type"] == "oauth"
        assert entry_dict["is_valid"] is True
        assert entry_dict["validation_count"] == 1
        assert entry_dict["has_user_info"] is True
        assert "created_at" in entry_dict
        assert "last_validated" in entry_dict


class TestConnectionPool:
    """Test HTTP connection pool functionality."""
    
    @pytest.fixture
    def connection_pool(self):
        """Create connection pool for testing."""
        return ConnectionPool(max_connections=10, max_keepalive=5)
    
    @pytest.fixture
    def mock_config(self):
        """Create mock SkyFi configuration."""
        config = MagicMock(spec=SkyFiConfig)
        config.url = "https://api.skyfi.com"
        config.timeout = 30
        config.ssl_verify = True
        config.custom_headers = None
        config.get_auth_method.return_value = "api_key"
        config.api_key = "test-api-key"
        return config
    
    def test_get_client_key(self, connection_pool, mock_config):
        """Test client key generation."""
        user_context = {"auth_token": "user-token", "auth_type": "bearer"}
        
        key = connection_pool.get_client_key(mock_config, user_context)
        
        assert key.startswith("https://api.skyfi.com:api_key:bearer:")
        assert len(key.split(":")) == 4
    
    def test_get_client_key_without_user_context(self, connection_pool, mock_config):
        """Test client key generation without user context."""
        user_context = {}
        
        key = connection_pool.get_client_key(mock_config, user_context)
        
        assert key == "https://api.skyfi.com:api_key"
    
    @patch('httpx.AsyncClient')
    async def test_get_or_create_client(self, mock_client_class, connection_pool, mock_config):
        """Test getting or creating HTTP client."""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client_class.return_value = mock_client
        
        user_context = {"auth_token": "test-token", "auth_type": "api_key"}
        
        client = await connection_pool.get_or_create_client(mock_config, user_context)
        
        assert client == mock_client
        mock_client_class.assert_called_once()
        
        # Test client reuse
        client2 = await connection_pool.get_or_create_client(mock_config, user_context)
        
        assert client2 == mock_client
        # Should not create new client
        assert mock_client_class.call_count == 1
    
    async def test_build_auth_headers_user_context(self, connection_pool, mock_config):
        """Test building auth headers with user context."""
        user_context = {"auth_token": "user-token", "auth_type": "bearer"}
        
        headers = await connection_pool._build_auth_headers(mock_config, user_context)
        
        assert headers["Authorization"] == "Bearer user-token"
        assert headers["User-Agent"] == "SkyFi-MCP-Factory/1.0"
        assert headers["Accept"] == "application/json"
    
    async def test_build_auth_headers_config_fallback(self, connection_pool, mock_config):
        """Test building auth headers with config fallback."""
        user_context = {}
        
        headers = await connection_pool._build_auth_headers(mock_config, user_context)
        
        assert headers["X-Skyfi-Api-Key"] == "test-api-key"
    
    def test_get_stats(self, connection_pool):
        """Test getting connection pool statistics."""
        stats = connection_pool.get_stats()
        
        assert "total_created" in stats
        assert "active_clients" in stats
        assert "max_connections" in stats
        assert stats["max_connections"] == 10
        assert stats["max_keepalive"] == 5


class TestSkyFiClientFactory:
    """Test SkyFi client factory functionality."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for testing."""
        return SkyFiClientFactory(
            credential_cache_ttl=60,
            credential_cache_size=100,
            connection_pool_size=50,
            enable_credential_validation=False  # Disable for testing
        )
    
    @pytest.fixture
    def mock_config(self):
        """Create mock SkyFi configuration."""
        config = MagicMock(spec=SkyFiConfig)
        config.url = "https://api.skyfi.com"
        config.timeout = 30
        config.ssl_verify = True
        config.custom_headers = None
        config.api_key = "test-api-key"
        config.oauth_access_token = None
        config.personal_token = None
        config.get_auth_method.return_value = "api_key"
        return config
    
    def test_determine_auth_credentials_user_context(self, factory, mock_config):
        """Test credential determination with user context."""
        user_context = {"auth_token": "user-token", "auth_type": "bearer"}
        
        auth_info = factory._determine_auth_credentials(user_context, mock_config)
        
        assert auth_info["token"] == "user-token"
        assert auth_info["type"] == "bearer"
    
    def test_determine_auth_credentials_oauth(self, factory, mock_config):
        """Test credential determination with OAuth."""
        mock_config.oauth_access_token = "oauth-token"
        user_context = {}
        
        auth_info = factory._determine_auth_credentials(user_context, mock_config)
        
        assert auth_info["token"] == "oauth-token"
        assert auth_info["type"] == "oauth"
    
    def test_determine_auth_credentials_api_key(self, factory, mock_config):
        """Test credential determination with API key."""
        user_context = {}
        
        auth_info = factory._determine_auth_credentials(user_context, mock_config)
        
        assert auth_info["token"] == "test-api-key"
        assert auth_info["type"] == "api_key"
    
    def test_determine_auth_credentials_personal_token(self, factory, mock_config):
        """Test credential determination with personal token."""
        mock_config.api_key = None
        mock_config.personal_token = "personal-token"
        user_context = {}
        
        auth_info = factory._determine_auth_credentials(user_context, mock_config)
        
        assert auth_info["token"] == "personal-token"
        assert auth_info["type"] == "personal_token"
    
    def test_determine_auth_credentials_none(self, factory, mock_config):
        """Test credential determination with no auth."""
        mock_config.api_key = None
        mock_config.oauth_access_token = None
        mock_config.personal_token = None
        user_context = {}
        
        with pytest.raises(SkyFiAuthenticationError):
            factory._determine_auth_credentials(user_context, mock_config)
    
    def test_try_fallback_auth(self, factory, mock_config):
        """Test fallback authentication."""
        mock_config.oauth_access_token = "oauth-token"
        mock_config.personal_token = "personal-token"
        
        # Test fallback from failed API key
        fallback = factory._try_fallback_auth({}, mock_config, "api_key")
        
        assert fallback["token"] == "oauth-token"
        assert fallback["type"] == "oauth"
        
        # Test fallback from failed OAuth
        fallback = factory._try_fallback_auth({}, mock_config, "oauth")
        
        assert fallback["token"] == "test-api-key"
        assert fallback["type"] == "api_key"
    
    def test_build_cache_key(self, factory):
        """Test cache key building."""
        auth_info = {"token": "test-token-123", "type": "api_key"}
        
        cache_key = factory._build_cache_key(auth_info)
        
        assert cache_key.startswith("api_key:")
        assert len(cache_key.split(":")[1]) == 32  # SHA256 hash truncated
    
    def test_cache_credential(self, factory):
        """Test credential caching."""
        entry = CredentialCacheEntry(
            credential="test-key",
            auth_type="api_key",
            is_valid=True
        )
        
        factory._cache_credential("test-key", entry)
        
        cached = factory._get_cached_credential("test-key")
        assert cached == entry
        assert cached.is_valid is True
    
    @patch('mcp_skyfi.skyfi.client.SkyFiClient')
    async def test_create_client_success(self, mock_client_class, factory, mock_config):
        """Test successful client creation."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        user_context = {"auth_token": "test-token", "auth_type": "api_key"}
        
        client = await factory.create_client(user_context, mock_config)
        
        assert client == mock_client
        mock_client_class.assert_called_once()
        
        # Check enhanced user context
        call_args = mock_client_class.call_args
        enhanced_context = call_args[1]["user_context"]
        assert enhanced_context["factory_created"] is True
        assert enhanced_context["auth_token"] == "test-token"
    
    async def test_create_client_validation_enabled(self, mock_config):
        """Test client creation with validation enabled."""
        factory = SkyFiClientFactory(enable_credential_validation=True)
        
        user_context = {"auth_token": "test-token", "auth_type": "api_key"}
        
        # Mock validation to fail, then succeed on fallback
        with patch.object(factory, '_validate_credentials') as mock_validate:
            mock_validate.return_value = {"is_valid": False, "error_message": "Invalid"}
            
            with pytest.raises(SkyFiAuthenticationError):
                await factory.create_client(user_context, mock_config)
    
    def test_get_factory_stats(self, factory):
        """Test getting factory statistics."""
        stats = factory.get_factory_stats()
        
        assert "factory" in stats
        assert "cache" in stats
        assert "connections" in stats
        assert "timestamp" in stats
        
        assert stats["factory"]["clients_created"] >= 0
        assert stats["cache"]["cache_size"] >= 0
        assert 0 <= stats["cache"]["cache_hit_rate"] <= 1
    
    def test_clear_credential_cache(self, factory):
        """Test clearing credential cache."""
        # Add some entries
        entry = CredentialCacheEntry("test", "api_key", True)
        factory._cache_credential("key1", entry)
        factory._cache_credential("key2", entry)
        
        cleared_count = factory.clear_credential_cache()
        
        assert cleared_count == 2
        assert factory._get_cached_credential("key1") is None
        assert factory._get_cached_credential("key2") is None


class TestFactoryGlobals:
    """Test global factory functions."""
    
    def test_get_client_factory_singleton(self):
        """Test global factory singleton behavior."""
        factory1 = get_client_factory()
        factory2 = get_client_factory()
        
        assert factory1 is factory2
    
    @patch('mcp_skyfi.skyfi.factory.get_client_factory')
    async def test_create_skyfi_client_convenience(self, mock_get_factory):
        """Test convenience function for client creation."""
        mock_factory = AsyncMock()
        mock_client = MagicMock()
        mock_factory.create_client.return_value = mock_client
        mock_get_factory.return_value = mock_factory
        
        user_context = {"auth_token": "test"}
        config = MagicMock()
        
        client = await create_skyfi_client(user_context, config)
        
        assert client == mock_client
        mock_factory.create_client.assert_called_once_with(user_context, config)


class TestFactoryThreadSafety:
    """Test factory thread safety."""
    
    @pytest.fixture
    def factory(self):
        """Create factory for testing."""
        return SkyFiClientFactory(
            credential_cache_ttl=60,
            credential_cache_size=100,
            enable_credential_validation=False
        )
    
    def test_concurrent_credential_caching(self, factory):
        """Test thread-safe credential caching."""
        results = []
        
        def cache_credential(thread_id):
            entry = CredentialCacheEntry(
                credential=f"key-{thread_id}",
                auth_type="api_key",
                is_valid=True
            )
            factory._cache_credential(f"key-{thread_id}", entry)
            
            cached = factory._get_cached_credential(f"key-{thread_id}")
            results.append(cached is not None)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_credential, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All caching operations should succeed
        assert all(results)
        assert len(results) == 10
    
    def test_concurrent_stats_access(self, factory):
        """Test thread-safe statistics access."""
        results = []
        
        def get_stats():
            stats = factory.get_factory_stats()
            results.append("factory" in stats and "cache" in stats)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=get_stats)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All stats access should succeed
        assert all(results)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])