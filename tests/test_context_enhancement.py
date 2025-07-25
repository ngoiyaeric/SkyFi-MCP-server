"""
Test MainAppContext Enhancement for Hive Mind Architecture

Tests the enhanced credential resolution system with 4-tier precedence hierarchy.
"""

import pytest
import os
from unittest.mock import Mock, patch
from typing import Dict, Any

# Import the enhanced context
import sys
sys.path.append('/Users/pskinnertech/Dev/gai/skyfi/mcp/src')

from mcp_skyfi.servers.context import MainAppContext
from mcp_skyfi.skyfi.config import SkyFiConfig
from mcp_skyfi.skyfi.client import SkyFiClientFactory
from mcp_skyfi.exceptions import SkyFiMCPError


class TestMainAppContextEnhancement:
    """Test enhanced MainAppContext with credential resolution."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock SkyFi config
        self.skyfi_config = Mock(spec=SkyFiConfig)
        self.skyfi_config.api_key = "server_api_key"
        self.skyfi_config.oauth_access_token = "server_oauth_token"
        self.skyfi_config.oauth_client_id = "server_client_id"
        self.skyfi_config.personal_token = "server_personal_token"
        self.skyfi_config.default_workspace = "test_workspace"
        self.skyfi_config.rate_limit = 100
        
        # Create main app context
        self.app_context = MainAppContext(
            skyfi_config=self.skyfi_config,
            service_status={"skyfi": True, "weather": True, "osm": True}
        )
    
    def test_client_credentials_precedence_level_1(self):
        """Test Level 1: Client credentials have highest precedence."""
        user_context = {
            "auth_token": "client_token",
            "auth_type": "bearer",
            "client_ip": "192.168.1.1",
            "request_id": "req_123"
        }
        
        credentials = self.app_context.get_effective_credentials(user_context, "skyfi")
        
        assert credentials["token"] == "client_token"
        assert credentials["type"] == "bearer"
        assert credentials["source"] == "client"
        assert credentials["precedence_level"] == 1
        assert credentials["metadata"]["client_ip"] == "192.168.1.1"
    
    def test_oauth_credentials_precedence_level_2(self):
        """Test Level 2: OAuth credentials when no client credentials."""
        user_context = {
            "oauth_access_token": "user_oauth_token",
            "oauth_scope": "read write",
            "user_id": "user_123"
        }
        
        credentials = self.app_context.get_effective_credentials(user_context, "skyfi")
        
        assert credentials["token"] == "user_oauth_token"
        assert credentials["type"] == "oauth"
        assert credentials["source"] == "oauth"
        assert credentials["precedence_level"] == 2
        assert credentials["metadata"]["scope"] == "read write"
    
    def test_server_credentials_precedence_level_3(self):
        """Test Level 3: Server credentials from configuration."""
        user_context = {}  # No user-provided credentials
        
        credentials = self.app_context.get_effective_credentials(user_context, "skyfi")
        
        assert credentials["token"] == "server_api_key"
        assert credentials["type"] == "api_key"
        assert credentials["source"] == "server_config"
        assert credentials["precedence_level"] == 3
        assert credentials["metadata"]["workspace"] == "test_workspace"
    
    @patch.dict(os.environ, {"SKYFI_API_KEY": "env_api_key"})
    def test_environment_credentials_precedence_level_4(self):
        """Test Level 4: Environment credentials as fallback."""
        # Remove server credentials
        self.app_context.skyfi_config.api_key = None
        self.app_context.skyfi_config.oauth_access_token = None
        self.app_context.skyfi_config.personal_token = None
        
        user_context = {}  # No user-provided credentials
        
        credentials = self.app_context.get_effective_credentials(user_context, "skyfi")
        
        assert credentials["token"] == "env_api_key"
        assert credentials["type"] == "api_key"
        assert credentials["source"] == "environment"
        assert credentials["precedence_level"] == 4
    
    def test_no_credentials_raises_error(self):
        """Test that missing credentials raise appropriate error."""
        # Clear all credentials
        self.app_context.skyfi_config.api_key = None
        self.app_context.skyfi_config.oauth_access_token = None
        self.app_context.skyfi_config.personal_token = None
        
        user_context = {}
        
        with pytest.raises(SkyFiMCPError) as exc_info:
            self.app_context.get_effective_credentials(user_context, "skyfi")
        
        assert "No valid credentials available" in str(exc_info.value)
    
    def test_service_specific_credential_resolution(self):
        """Test service-specific credential resolution."""
        user_context = {"auth_token": "client_token", "auth_type": "api_key"}
        
        skyfi_creds = self.app_context.get_service_credentials("skyfi", user_context)
        
        assert skyfi_creds["token"] == "client_token"
        assert skyfi_creds["service"] == "skyfi"
    
    def test_thread_safe_context_update(self):
        """Test thread-safe user context updates."""
        import threading
        import time
        
        updates = []
        
        def update_context(update_data):
            self.app_context.update_user_context_safe(update_data)
            updates.append(self.app_context.user_context.copy())
        
        # Create multiple threads updating context simultaneously
        threads = []
        for i in range(5):
            thread_data = {"thread_id": i, "timestamp": time.time()}
            thread = threading.Thread(target=update_context, args=(thread_data,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all updates were applied
        assert len(updates) == 5
        assert all("thread_id" in update for update in updates)
    
    def test_credential_validation(self):
        """Test credential validation for different services."""
        # Valid SkyFi credentials
        skyfi_creds = {
            "token": "test_token",
            "type": "api_key",
            "source": "client",
            "precedence_level": 1
        }
        assert self.app_context._validate_credentials_for_service(skyfi_creds, "skyfi")
        
        # Invalid credentials (empty token)
        invalid_creds = {
            "token": "",
            "type": "api_key",
            "source": "client",
            "precedence_level": 1
        }
        assert not self.app_context._validate_credentials_for_service(invalid_creds, "skyfi")
    
    def test_credential_summary(self):
        """Test credential summary generation for monitoring."""
        user_context = {"auth_token": "test_token", "auth_type": "bearer"}
        self.app_context.update_user_context_safe(user_context)
        
        summary = self.app_context.get_credential_summary()
        
        assert "services" in summary
        assert "skyfi" in summary["services"]
        assert summary["services"]["skyfi"]["available"] is True
        assert summary["user_context_available"] is True
    
    def test_backward_compatibility(self):
        """Test that all existing methods still work."""
        # Test existing methods
        assert self.app_context.is_service_available("skyfi") is True
        assert self.app_context.get_service_config("skyfi") == self.skyfi_config
        assert self.app_context.is_tool_enabled("test_tool") is True
        assert self.app_context.can_execute_write_operation() is True
        
        # Test user context methods
        self.app_context.update_user_context(auth_token="test")
        assert self.app_context.get_user_auth_token() == "test"
        assert self.app_context.has_user_auth() is True


class TestSkyFiClientFactory:
    """Test SkyFiClientFactory integration with enhanced context."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.skyfi_config = Mock(spec=SkyFiConfig)
        self.skyfi_config.api_key = "server_api_key"
        
        self.app_context = MainAppContext(
            skyfi_config=self.skyfi_config,
            service_status={"skyfi": True}
        )
    
    @pytest.mark.asyncio
    async def test_create_client_with_credential_resolution(self):
        """Test client creation with automatic credential resolution."""
        user_context = {"auth_token": "client_token", "auth_type": "bearer"}
        
        client = await SkyFiClientFactory.create_client(
            self.app_context, user_context, "skyfi"
        )
        
        assert client is not None
        assert client.user_context["auth_token"] == "client_token"
        assert client.user_context["effective_credentials"]["precedence_level"] == 1
    
    @pytest.mark.asyncio
    async def test_create_authenticated_client_override(self):
        """Test client creation with explicit authentication override."""
        client = await SkyFiClientFactory.create_authenticated_client(
            self.app_context, "override_token", "api_key"
        )
        
        assert client is not None
        assert client.user_context["auth_token"] == "override_token"
        assert client.user_context["effective_credentials"]["source"] == "client_override"
    
    def test_validate_credentials(self):
        """Test credential validation in factory."""
        valid_creds = {
            "token": "test_token",
            "type": "api_key", 
            "source": "client",
            "precedence_level": 1
        }
        assert SkyFiClientFactory.validate_credentials(valid_creds) is True
        
        invalid_creds = {"token": ""}  # Missing required fields
        assert SkyFiClientFactory.validate_credentials(invalid_creds) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])