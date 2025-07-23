# SkyFi MCP Server Testing Framework

## Comprehensive Testing Strategy and Quality Assurance Plan

This document outlines the testing architecture, strategies, and quality gates for the SkyFi MCP (Model Context Protocol) server, designed to ensure production readiness through systematic validation of all architectural components.

### Architecture Overview

The SkyFi MCP server employs a sophisticated multi-layered architecture requiring comprehensive testing across:

- **MCP Transport Layer** - STDIO, SSE, Streamable HTTP protocols
- **FastMCP Server Layer** - Framework integration and tool filtering
- **Service Layer** - SkyFi, OSM, Weather services with independent authentication
- **Authentication Layer** - Multi-method security (OAuth, PAT, API Keys, JWT, Service Accounts)
- **Data Processing Layer** - Model transformation and validation
- **Network Layer** - HTTP clients and external API management

## Testing Architecture Pattern

### 1. Test Organization Structure

```
tests/
├── unit/                    # Isolated component testing
│   ├── models/             # Data model validation
│   ├── services/           # Business logic testing  
│   ├── middleware/         # Auth and rate limiting
│   ├── utils/              # Utility functions
│   └── mcp/                # MCP protocol handlers
├── integration/            # Service interaction testing
│   ├── auth/               # Multi-method auth flows
│   ├── services/           # Cross-service operations
│   ├── mcp_protocol/       # End-to-end MCP compliance
│   └── external_apis/      # External service mocking
├── performance/            # Load and benchmark testing
│   ├── benchmarks/         # Performance benchmarks
│   ├── load_tests/         # Concurrent request handling
│   └── memory_profiling/   # Resource usage analysis
├── security/               # Security validation
│   ├── auth_penetration/   # Authentication bypass attempts
│   ├── input_validation/   # Injection and fuzzing tests
│   └── rate_limiting/      # DOS protection validation
├── fixtures/               # Test data and mocks
│   ├── auth_tokens/        # Authentication test data
│   ├── api_responses/      # External API mock responses
│   └── test_configs/       # Environment configurations
└── e2e/                    # End-to-end scenarios
    ├── user_workflows/     # Complete user journeys
    ├── cli_integration/    # Command-line interface testing
    └── client_sdk/         # SDK compatibility testing
```

### 2. Mock Strategy for External Services

#### SkyFi API Mocking
```python
# tests/fixtures/skyfi_mock.py
class SkyFiAPIMock:
    """Comprehensive SkyFi API mock with realistic responses"""
    
    def __init__(self):
        self.mock_server = MockServer()
        self.auth_responses = self._load_auth_responses()
        self.archive_responses = self._load_archive_responses()
        
    async def setup_auth_scenarios(self):
        """Setup various authentication scenarios"""
        # Valid API key
        self.mock_server.add_route(
            "GET", "/auth/whoami",
            response=self.auth_responses["valid_user"],
            headers={"X-Skyfi-Api-Key": "valid_key_123"}
        )
        
        # Invalid API key
        self.mock_server.add_route(
            "GET", "/auth/whoami", 
            response={"detail": "Authentication failed"},
            status=401,
            headers={"X-Skyfi-Api-Key": "invalid_key"}
        )
        
        # Rate limited scenario
        self.mock_server.add_route(
            "GET", "/auth/whoami",
            response={"detail": "Rate limit exceeded"}, 
            status=429,
            delay=0.1  # Simulate rate limit delay
        )
```

#### Weather Service Mocking
```python
# tests/fixtures/weather_mock.py
class WeatherAPIMock:
    """OpenWeatherMap and custom weather service mocks"""
    
    def setup_weather_scenarios(self):
        # Current weather response
        self.add_route(
            "GET", "/weather",
            response={
                "coord": {"lon": -122.08, "lat": 37.39},
                "weather": [{"main": "Clear", "description": "clear sky"}],
                "main": {"temp": 282.55, "pressure": 1023, "humidity": 100}
            }
        )
        
        # Weather service unavailable
        self.add_route(
            "GET", "/weather",
            response={"error": "Service temporarily unavailable"},
            status=503
        )
```

#### OSM Service Mocking  
```python
# tests/fixtures/osm_mock.py
class OSMAPIMock:
    """OpenStreetMap Nominatim API mock"""
    
    def setup_geocoding_scenarios(self):
        # Successful geocoding
        self.add_route(
            "GET", "/search",
            response=[{
                "place_id": 12345,
                "licence": "© OpenStreetMap contributors",
                "display_name": "San Francisco, California, USA",
                "lat": "37.7749295",
                "lon": "-122.4194155"
            }]
        )
        
        # No results found
        self.add_route(
            "GET", "/search", 
            response=[]
        )
```

### 3. Authentication Testing Framework

#### Multi-Method Authentication Test Suite
```python
# tests/integration/auth/test_multi_auth.py
import pytest
from tests.fixtures.auth_mock import AuthenticationMockSuite

class TestMultiMethodAuthentication:
    """Comprehensive authentication method testing"""
    
    @pytest.fixture
    def auth_suite(self):
        return AuthenticationMockSuite()
    
    async def test_oauth_precedence(self, auth_suite):
        """Test OAuth 2.0 takes precedence over other methods"""
        request_headers = {
            "Authorization": "Bearer valid_oauth_token",
            "X-Skyfi-Api-Key": "valid_api_key",
            "X-PAT-Token": "valid_pat_token"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        assert auth_result.method == "oauth"
        assert auth_result.user_id is not None
        
    async def test_pat_fallback(self, auth_suite):
        """Test PAT authentication when OAuth fails"""
        request_headers = {
            "Authorization": "Bearer invalid_oauth_token",
            "X-PAT-Token": "valid_pat_token"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        assert auth_result.method == "pat"
        
    async def test_api_key_legacy_support(self, auth_suite):
        """Test API key backward compatibility"""
        request_headers = {
            "X-Skyfi-Api-Key": "sk_valid_api_key_123"
        }
        
        auth_result = await auth_suite.authenticate(request_headers)
        assert auth_result.method == "api_key"
        assert auth_result.scopes == ["read:archives", "write:orders"]
        
    @pytest.mark.parametrize("invalid_method", [
        {"Authorization": "Bearer invalid_token"},
        {"X-PAT-Token": "expired_pat_token"},
        {"X-Skyfi-Api-Key": "revoked_api_key"},
        {"X-Service-Account-Key": "invalid_service_key"}
    ])
    async def test_authentication_failures(self, auth_suite, invalid_method):
        """Test various authentication failure scenarios"""
        with pytest.raises(AuthenticationError):
            await auth_suite.authenticate(invalid_method)
```

#### Rate Limiting and Security Testing
```python
# tests/security/test_rate_limiting.py
class TestRateLimitingSecurity:
    """Rate limiting and DOS protection testing"""
    
    async def test_rate_limit_per_api_key(self):
        """Test rate limiting per API key"""
        api_key = "test_rate_limit_key"
        
        # Make requests up to the limit
        for i in range(100):  # Assuming 100 req/min limit
            response = await self.client.get(
                "/skyfi/search-archives",
                headers={"X-Skyfi-Api-Key": api_key}
            )
            assert response.status_code == 200
            
        # 101st request should be rate limited
        response = await self.client.get(
            "/skyfi/search-archives", 
            headers={"X-Skyfi-Api-Key": api_key}
        )
        assert response.status_code == 429
        assert "X-RateLimit-Remaining" in response.headers
        
    async def test_rate_limit_bypass_attempts(self):
        """Test rate limit bypass prevention"""
        api_key = "test_bypass_key"
        
        # Attempt various bypass techniques
        bypass_headers = [
            {"X-Skyfi-Api-Key": api_key, "X-Forwarded-For": "different.ip"},
            {"X-Skyfi-Api-Key": api_key, "User-Agent": "Different-Agent"},
            {"X-Skyfi-Api-Key": api_key.upper()},  # Case variation
        ]
        
        # Exhaust rate limit first
        for i in range(100):
            await self.client.get("/skyfi/search-archives", headers={"X-Skyfi-Api-Key": api_key})
            
        # Test bypass attempts
        for headers in bypass_headers:
            response = await self.client.get("/skyfi/search-archives", headers=headers)
            assert response.status_code == 429, f"Bypass attempt succeeded with headers: {headers}"
```

### 4. MCP Protocol Compliance Testing

#### MCP Protocol Validation Suite
```python
# tests/mcp_protocol/test_compliance.py
class TestMCPCompliance:
    """Comprehensive MCP protocol compliance testing"""
    
    async def test_mcp_initialization_stdio(self):
        """Test MCP server initialization via STDIO"""
        process = await asyncio.create_subprocess_exec(
            "python", "-m", "mcp_skyfi", "--transport", "stdio",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Send MCP initialization message
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        process.stdin.write(json.dumps(init_message).encode() + b'\n')
        await process.stdin.drain()
        
        # Read and validate initialization response
        response_line = await process.stdout.readline()
        response = json.loads(response_line.decode())
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        
        process.terminate()
        
    async def test_mcp_tool_discovery(self):
        """Test MCP tool discovery and listing"""
        # Send tools/list request
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        response = await self.send_mcp_message(list_tools_message)
        
        assert "result" in response
        assert "tools" in response["result"]
        
        tools = response["result"]["tools"]
        assert len(tools) > 0
        
        # Validate each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            
    async def test_mcp_tool_execution(self):
        """Test MCP tool execution with various inputs"""
        # Test SkyFi archive search tool
        execute_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "skyfi_search_archives",
                "arguments": {
                    "aoi": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.5, 37.7], [-122.4, 37.7],
                            [-122.4, 37.8], [-122.5, 37.8],
                            [-122.5, 37.7]
                        ]]
                    },
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            }
        }
        
        response = await self.send_mcp_message(execute_message)
        
        assert "result" in response
        assert "content" in response["result"]
        
        # Validate response content structure
        content = response["result"]["content"]
        assert isinstance(content, list)
        assert len(content) > 0
        assert content[0]["type"] in ["text", "image", "resource"]
```

### 5. Performance Testing and Benchmarking

#### Load Testing Framework
```python
# tests/performance/test_load.py
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

class TestPerformanceLoad:
    """Performance and load testing suite"""
    
    async def test_concurrent_requests_performance(self):
        """Test server performance under concurrent load"""
        concurrent_users = 50
        requests_per_user = 20
        
        async def user_simulation():
            """Simulate a user making multiple requests"""
            response_times = []
            
            for i in range(requests_per_user):
                start_time = time.time()
                
                response = await self.client.get(
                    "/skyfi/search-archives",
                    headers={"X-Skyfi-Api-Key": "performance_test_key"},
                    json={
                        "aoi": self.test_aoi,
                        "start_date": "2024-01-01", 
                        "end_date": "2024-01-31"
                    }
                )
                
                end_time = time.time()
                response_times.append(end_time - start_time)
                
                assert response.status_code == 200
                
            return response_times
        
        # Run concurrent user simulations
        tasks = [user_simulation() for _ in range(concurrent_users)]
        all_response_times = await asyncio.gather(*tasks)
        
        # Flatten response times
        flat_times = [time for user_times in all_response_times for time in user_times]
        
        # Calculate performance metrics
        avg_response_time = statistics.mean(flat_times)
        p95_response_time = statistics.quantiles(flat_times, n=20)[18]  # 95th percentile
        max_response_time = max(flat_times)
        
        # Performance assertions
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time}s"
        assert p95_response_time < 5.0, f"95th percentile too high: {p95_response_time}s" 
        assert max_response_time < 10.0, f"Maximum response time too high: {max_response_time}s"
        
    async def test_memory_usage_under_load(self):
        """Test memory usage and leak detection"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate sustained load
        for batch in range(10):
            tasks = []
            for i in range(100):
                task = self.client.get("/skyfi/search-archives", 
                                     headers={"X-Skyfi-Api-Key": "memory_test_key"})
                tasks.append(task)
                
            await asyncio.gather(*tasks)
            
            # Check memory usage
            current_memory = process.memory_info().rss
            memory_increase = (current_memory - initial_memory) / (1024 * 1024)  # MB
            
            # Memory should not increase more than 100MB per batch
            assert memory_increase < 100, f"Memory leak detected: {memory_increase}MB increase"
```

#### Benchmark Suite
```python
# tests/performance/benchmarks.py
class TestBenchmarks:
    """Performance benchmarks for key operations"""
    
    def test_authentication_performance(self):
        """Benchmark authentication method performance"""
        auth_methods = {
            "api_key": {"X-Skyfi-Api-Key": "benchmark_key"},
            "bearer": {"Authorization": "Bearer benchmark_token"}, 
            "pat": {"X-PAT-Token": "benchmark_pat_token"}
        }
        
        results = {}
        
        for method, headers in auth_methods.items():
            times = []
            
            for _ in range(1000):
                start = time.perf_counter()
                
                # Simulate authentication
                auth_result = self.auth_middleware.authenticate(headers)
                
                end = time.perf_counter()
                times.append(end - start)
                
            results[method] = {
                "avg": statistics.mean(times),
                "min": min(times),
                "max": max(times),
                "p95": statistics.quantiles(times, n=20)[18]
            }
        
        # Authentication should be sub-millisecond on average
        for method, metrics in results.items():
            assert metrics["avg"] < 0.001, f"{method} auth too slow: {metrics['avg']}s"
            assert metrics["p95"] < 0.005, f"{method} p95 too slow: {metrics['p95']}s"
```

### 6. Security Testing Protocols

#### Security Vulnerability Testing
```python
# tests/security/test_vulnerabilities.py  
class TestSecurityVulnerabilities:
    """Security vulnerability and penetration testing"""
    
    async def test_sql_injection_prevention(self):
        """Test SQL injection attack prevention"""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR 1=1 --",
            "' UNION SELECT * FROM api_keys --",
            "admin'--",
            "' OR 'x'='x"
        ]
        
        for payload in injection_payloads:
            response = await self.client.get(
                f"/skyfi/search-archives?query={payload}",
                headers={"X-Skyfi-Api-Key": "security_test_key"}
            )
            
            # Should not return sensitive data or cause errors
            assert response.status_code in [400, 422], f"Injection payload succeeded: {payload}"
            assert "error" not in response.text.lower()
            
    async def test_xss_prevention(self):
        """Test Cross-Site Scripting (XSS) prevention"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            response = await self.client.post(
                "/skyfi/create-order",
                headers={"X-Skyfi-Api-Key": "security_test_key"},
                json={"description": payload}
            )
            
            # Response should not contain unescaped payload
            assert payload not in response.text
            assert "script" not in response.text.lower()
            
    async def test_authentication_bypass_attempts(self):
        """Test authentication bypass prevention"""
        bypass_attempts = [
            # Missing authentication
            {},
            # Malformed headers
            {"Authorization": "Bearer "},
            {"X-Skyfi-Api-Key": ""},
            # Header injection attempts
            {"X-Skyfi-Api-Key": "valid_key\nX-Admin: true"},
            # Case sensitivity bypass
            {"x-skyfi-api-key": "valid_key"},
            {"AUTHORIZATION": "Bearer valid_token"}
        ]
        
        for headers in bypass_attempts:
            response = await self.client.get("/skyfi/search-archives", headers=headers)
            assert response.status_code == 401, f"Auth bypass succeeded: {headers}"
```

### 7. Continuous Integration and Quality Gates

#### CI/CD Pipeline Configuration
```yaml
# .github/workflows/test-suite.yml
name: SkyFi MCP Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
        
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=src/mcp_skyfi --cov-report=xml
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      redis:
        image: redis
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
        
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --tb=short
        
    - name: Run MCP compliance tests
      run: |
        pytest tests/mcp_protocol/ -v

  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
        
    - name: Install security testing tools
      run: |
        pip install bandit safety semgrep
        
    - name: Run security vulnerability scan
      run: |
        bandit -r src/ -f json -o bandit-results.json
        safety check --json --output safety-results.json
        semgrep --config=auto src/
        
    - name: Run security tests
      run: |
        pytest tests/security/ -v

  performance-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
        
    - name: Run performance benchmarks
      run: |
        pytest tests/performance/ -v --benchmark-only
        
    - name: Performance regression check
      run: |
        python scripts/performance_regression_check.py

  quality-gates:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, security-tests, performance-tests]
    
    steps:
    - name: Check quality gates
      run: |
        echo "All tests passed - Quality gates satisfied"
```

#### Quality Gates Configuration
```python
# tests/quality_gates.py
class QualityGates:
    """Quality gates for production readiness"""
    
    QUALITY_REQUIREMENTS = {
        "code_coverage": 85,  # Minimum 85% test coverage
        "security_score": 9.0,  # Minimum security score out of 10
        "performance_p95": 2.0,  # 95th percentile response time < 2s
        "memory_usage_mb": 512,  # Maximum memory usage under load
        "error_rate": 0.01,  # Maximum 1% error rate
        "availability": 99.9,  # Minimum 99.9% availability
    }
    
    def check_quality_gates(self, test_results):
        """Check if all quality gates are satisfied"""
        gates_passed = []
        
        # Code Coverage Gate
        coverage = test_results.get("coverage_percentage", 0)
        gates_passed.append(("Code Coverage", coverage >= self.QUALITY_REQUIREMENTS["code_coverage"]))
        
        # Security Gate  
        security_score = test_results.get("security_score", 0)
        gates_passed.append(("Security Score", security_score >= self.QUALITY_REQUIREMENTS["security_score"]))
        
        # Performance Gate
        p95_response_time = test_results.get("p95_response_time", float('inf'))
        gates_passed.append(("Performance P95", p95_response_time <= self.QUALITY_REQUIREMENTS["performance_p95"]))
        
        # Memory Usage Gate
        max_memory_mb = test_results.get("max_memory_mb", float('inf'))
        gates_passed.append(("Memory Usage", max_memory_mb <= self.QUALITY_REQUIREMENTS["memory_usage_mb"]))
        
        # Error Rate Gate
        error_rate = test_results.get("error_rate", 1.0)
        gates_passed.append(("Error Rate", error_rate <= self.QUALITY_REQUIREMENTS["error_rate"]))
        
        all_passed = all(passed for _, passed in gates_passed)
        
        return {
            "all_gates_passed": all_passed,
            "gate_results": gates_passed,
            "summary": f"Quality Gates: {sum(1 for _, passed in gates_passed if passed)}/{len(gates_passed)} passed"
        }
```

### 8. Testing Best Practices and Guidelines

#### Test Development Guidelines

1. **Test Independence**: Each test should be fully independent and runnable in isolation
2. **Realistic Data**: Use realistic test data that matches production scenarios
3. **Error Scenarios**: Test both happy path and error conditions extensively
4. **Performance Awareness**: Include performance assertions in functional tests
5. **Security First**: Every test should validate security assumptions
6. **Documentation**: Tests serve as living documentation of expected behavior

#### Mock and Fixture Management
```python
# tests/conftest.py
@pytest.fixture(scope="session")
async def test_server():
    """Start test server instance"""
    server = await start_test_server()
    yield server
    await server.shutdown()

@pytest.fixture
def auth_headers():
    """Provide various authentication header combinations"""
    return {
        "valid_api_key": {"X-Skyfi-Api-Key": "test_valid_key_123"},
        "valid_oauth": {"Authorization": "Bearer test_oauth_token"},
        "valid_pat": {"X-PAT-Token": "test_pat_token_456"},
        "invalid_key": {"X-Skyfi-Api-Key": "invalid_key"},
        "expired_token": {"Authorization": "Bearer expired_token"}
    }
    
@pytest.fixture
def external_service_mocks():
    """Setup external service mocks"""
    with ExternalServiceMockSuite() as mock_suite:
        yield mock_suite
```

This comprehensive testing strategy ensures the SkyFi MCP server meets enterprise-grade quality, security, and performance requirements through systematic validation of all architectural components.