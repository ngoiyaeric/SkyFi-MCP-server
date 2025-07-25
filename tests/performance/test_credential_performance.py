"""
Credential Performance Testing Suite

This module provides comprehensive performance testing for credential handling
in the SkyFi MCP server, including validation speed, memory usage optimization,
concurrent operations, and caching effectiveness.
"""

from __future__ import annotations

import asyncio
import gc
import psutil
import pytest
import statistics
import time
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from tests.fixtures.credential_mocks import (
    DynamicCredentialMock,
    MultiServiceCredentialCoordinator,
    CredentialContext
)


@pytest.mark.performance
@pytest.mark.auth
@pytest.mark.slow
class TestCredentialPerformance:
    """Comprehensive credential performance testing suite."""
    
    @pytest.fixture
    async def credential_mock(self):
        """Provide dynamic credential mock."""
        mock = DynamicCredentialMock()
        yield mock
    
    @pytest.fixture
    async def coordinator(self):
        """Provide credential coordinator."""
        return MultiServiceCredentialCoordinator()
    
    @pytest.fixture
    def performance_monitor(self):
        """Provide performance monitoring utilities."""
        class PerformanceMonitor:
            def __init__(self):
                self.metrics = {}
                
            def start_timing(self, operation: str):
                self.metrics[operation] = {"start": time.perf_counter()}
                
            def stop_timing(self, operation: str) -> float:
                if operation in self.metrics:
                    duration = time.perf_counter() - self.metrics[operation]["start"]
                    self.metrics[operation]["duration"] = duration
                    return duration
                return 0.0
                
            def get_memory_usage(self) -> float:
                """Get current memory usage in MB."""
                process = psutil.Process()
                return process.memory_info().rss / (1024 * 1024)
        
        return PerformanceMonitor()
    
    async def test_credential_injection_speed(self, credential_mock, performance_monitor):
        """Test speed of credential injection operations."""
        # Test single service injection speed
        single_service_times = []
        
        for i in range(100):
            performance_monitor.start_timing(f"single_injection_{i}")
            
            injection_result = await credential_mock.inject_credentials(
                request_context={"speed_test": i},
                required_services={"skyfi"}
            )
            
            duration = performance_monitor.stop_timing(f"single_injection_{i}")
            single_service_times.append(duration)
            
            assert injection_result.success
        
        # Analyze single service performance
        avg_single_time = statistics.mean(single_service_times)
        median_single_time = statistics.median(single_service_times)
        p95_single_time = sorted(single_service_times)[int(0.95 * len(single_service_times))]
        
        # Performance requirements
        assert avg_single_time < 0.01, f"Average single injection too slow: {avg_single_time:.4f}s"
        assert p95_single_time < 0.02, f"P95 single injection too slow: {p95_single_time:.4f}s"
        
        # Test multi-service injection speed
        multi_service_times = []
        
        for i in range(50):
            performance_monitor.start_timing(f"multi_injection_{i}")
            
            injection_result = await credential_mock.inject_credentials(
                request_context={"multi_speed_test": i},
                required_services={"skyfi", "weather", "osm"}
            )
            
            duration = performance_monitor.stop_timing(f"multi_injection_{i}")
            multi_service_times.append(duration)
            
            assert injection_result.success
        
        # Analyze multi-service performance
        avg_multi_time = statistics.mean(multi_service_times)
        p95_multi_time = sorted(multi_service_times)[int(0.95 * len(multi_service_times))]
        
        # Multi-service should be reasonable (3x single service max)
        assert avg_multi_time < 0.03, f"Average multi injection too slow: {avg_multi_time:.4f}s"
        assert p95_multi_time < 0.05, f"P95 multi injection too slow: {p95_multi_time:.4f}s"
        
        print(f"\nCredential Injection Performance:")
        print(f"Single Service - Avg: {avg_single_time*1000:.2f}ms, P95: {p95_single_time*1000:.2f}ms")
        print(f"Multi Service - Avg: {avg_multi_time*1000:.2f}ms, P95: {p95_multi_time*1000:.2f}ms")
    
    async def test_concurrent_injection_performance(self, credential_mock, performance_monitor):
        """Test performance under concurrent credential injection load."""
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            # Create concurrent injection tasks
            tasks = []
            start_time = time.perf_counter()
            
            for i in range(concurrency):
                task = credential_mock.inject_credentials(
                    request_context={"concurrent_test": i, "concurrency": concurrency},
                    required_services={"skyfi", "weather"}
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            injection_results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()
            
            # Analyze results
            total_time = end_time - start_time
            successful_injections = sum(
                1 for result in injection_results 
                if isinstance(result, dict) and result.success
            )
            
            throughput = successful_injections / total_time if total_time > 0 else 0
            avg_response_time = total_time / len(injection_results) if injection_results else 0
            
            results[concurrency] = {
                "total_time": total_time,
                "successful_injections": successful_injections,
                "throughput": throughput,
                "avg_response_time": avg_response_time
            }
            
            # Performance requirements
            assert successful_injections >= concurrency * 0.95, (
                f"Too many failures at concurrency {concurrency}: "
                f"{successful_injections}/{concurrency}"
            )
            
            assert avg_response_time < 0.1, (
                f"Average response time too slow at concurrency {concurrency}: "
                f"{avg_response_time:.4f}s"
            )
        
        # Verify throughput scales reasonably
        baseline_throughput = results[1]["throughput"]
        
        for concurrency in [5, 10, 20]:
            if concurrency in results:
                current_throughput = results[concurrency]["throughput"]
                scaling_factor = current_throughput / baseline_throughput
                
                # Should achieve at least 50% scaling efficiency
                min_expected_scaling = concurrency * 0.5
                assert scaling_factor >= min_expected_scaling, (
                    f"Poor scaling at concurrency {concurrency}: "
                    f"factor={scaling_factor:.2f}, expected>={min_expected_scaling:.2f}"
                )
        
        print(f"\nConcurrent Injection Performance:")
        for concurrency, metrics in results.items():
            print(f"Concurrency {concurrency}: {metrics['throughput']:.1f} ops/sec, "
                  f"Avg: {metrics['avg_response_time']*1000:.2f}ms")
    
    async def test_memory_usage_optimization(self, credential_mock, performance_monitor):
        """Test memory usage and optimization for credential operations."""
        # Baseline memory measurement
        gc.collect()  # Force garbage collection
        baseline_memory = performance_monitor.get_memory_usage()
        
        # Perform many credential injections
        credentials_created = []
        
        for i in range(1000):
            injection_result = await credential_mock.inject_credentials(
                request_context={"memory_test": i},
                required_services={"skyfi", "weather"}
            )
            
            if injection_result.success:
                credentials_created.append(injection_result.injected_credentials)
            
            # Check memory every 100 operations
            if i % 100 == 0:
                current_memory = performance_monitor.get_memory_usage()
                memory_increase = current_memory - baseline_memory
                
                # Memory should not grow excessively
                max_allowed_increase = 50 + (i * 0.01)  # 50MB base + 10KB per operation
                assert memory_increase < max_allowed_increase, (
                    f"Excessive memory growth at operation {i}: "
                    f"{memory_increase:.2f}MB > {max_allowed_increase:.2f}MB"
                )
        
        # Final memory check
        final_memory = performance_monitor.get_memory_usage()
        total_memory_increase = final_memory - baseline_memory
        
        # Should not use more than 100MB for 1000 operations
        assert total_memory_increase < 100, (
            f"Total memory usage too high: {total_memory_increase:.2f}MB"
        )
        
        # Test memory cleanup after operations
        credentials_created.clear()
        gc.collect()
        
        # Allow some time for cleanup
        await asyncio.sleep(0.1)
        
        cleanup_memory = performance_monitor.get_memory_usage()
        memory_after_cleanup = cleanup_memory - baseline_memory
        
        # Memory should decrease after cleanup
        assert memory_after_cleanup < total_memory_increase * 0.8, (
            f"Poor memory cleanup: {memory_after_cleanup:.2f}MB still used "
            f"(was {total_memory_increase:.2f}MB)"
        )
        
        print(f"\nMemory Usage Analysis:")
        print(f"Baseline: {baseline_memory:.2f}MB")
        print(f"Peak: {final_memory:.2f}MB (+{total_memory_increase:.2f}MB)")
        print(f"After cleanup: {cleanup_memory:.2f}MB (+{memory_after_cleanup:.2f}MB)")
    
    async def test_credential_caching_performance(self, credential_mock):
        """Test performance benefits of credential caching."""
        # Reset metrics to get clean cache measurements
        credential_mock.reset_metrics()
        
        # Test cache miss scenario (first requests)
        cache_miss_times = []
        
        for i in range(20):
            start_time = time.perf_counter()
            
            injection_result = await credential_mock.inject_credentials(
                request_context={"cache_test_miss": i},
                required_services={"skyfi"}
            )
            
            end_time = time.perf_counter()
            cache_miss_times.append(end_time - start_time)
            
            assert injection_result.success
        
        # Test cache hit scenario (repeated requests with same context)
        cache_hit_times = []
        
        for i in range(20):
            start_time = time.perf_counter()
            
            injection_result = await credential_mock.inject_credentials(
                request_context={"cache_test_hit": "same_context"},  # Same context
                required_services={"skyfi"}
            )
            
            end_time = time.perf_counter()
            cache_hit_times.append(end_time - start_time)
            
            assert injection_result.success
        
        # Analyze cache performance
        avg_miss_time = statistics.mean(cache_miss_times)
        avg_hit_time = statistics.mean(cache_hit_times)
        
        # Cache hits should be faster than misses
        performance_improvement = (avg_miss_time - avg_hit_time) / avg_miss_time
        
        # Should see at least 10% improvement from caching
        assert performance_improvement > 0.1, (
            f"Insufficient cache performance improvement: {performance_improvement:.2%}"
        )
        
        # Verify cache metrics
        metrics = credential_mock.get_injection_metrics()
        
        assert metrics["credential_cache_hits"] > 0, "No cache hits recorded"
        assert metrics["credential_cache_misses"] > 0, "No cache misses recorded"
        
        cache_hit_ratio = (
            metrics["credential_cache_hits"] / 
            (metrics["credential_cache_hits"] + metrics["credential_cache_misses"])
        )
        
        # Should have reasonable cache hit ratio for repeated requests
        assert cache_hit_ratio > 0.3, f"Poor cache hit ratio: {cache_hit_ratio:.2%}"
        
        print(f"\nCache Performance Analysis:")
        print(f"Cache Miss Avg: {avg_miss_time*1000:.2f}ms")
        print(f"Cache Hit Avg: {avg_hit_time*1000:.2f}ms")
        print(f"Performance Improvement: {performance_improvement:.2%}")
        print(f"Cache Hit Ratio: {cache_hit_ratio:.2%}")
    
    async def test_credential_validation_speed(self, credential_mock):
        """Test speed of credential validation operations."""
        # Add various types of credentials for validation testing
        test_credentials = [
            ("oauth", "oauth_validation_test_token", {"expires_at": time.time() + 3600}),
            ("api_key", "sk_validation_test_key_123", {}),
            ("pat", "skyfi_pat_validation_token", {"expires_at": time.time() + 86400}),
            ("jwt", "jwt_validation_test_token", {"expires_at": time.time() + 1800}),
        ]
        
        validation_times = []
        
        for cred_type, cred_value, cred_kwargs in test_credentials:
            # Add credential
            credential_mock.add_credential(
                "validation_test_service", cred_type, cred_value, **cred_kwargs
            )
            
            # Test validation speed
            for i in range(50):
                start_time = time.perf_counter()
                
                injection_result = await credential_mock.inject_credentials(
                    request_context={"validation_test": i, "cred_type": cred_type},
                    required_services={"validation_test_service"}
                )
                
                end_time = time.perf_counter()
                validation_times.append(end_time - start_time)
                
                assert injection_result.success
                
                # Verify correct credential was selected
                injected_cred = injection_result.injected_credentials["validation_test_service"]
                assert injected_cred.credential_type == cred_type
        
        # Analyze validation performance
        avg_validation_time = statistics.mean(validation_times)
        p95_validation_time = sorted(validation_times)[int(0.95 * len(validation_times))]
        
        # Validation should be very fast
        assert avg_validation_time < 0.005, (
            f"Average validation too slow: {avg_validation_time:.4f}s"
        )
        assert p95_validation_time < 0.01, (
            f"P95 validation too slow: {p95_validation_time:.4f}s"
        )
        
        print(f"\nCredential Validation Performance:")
        print(f"Average: {avg_validation_time*1000:.2f}ms")
        print(f"P95: {p95_validation_time*1000:.2f}ms")
    
    async def test_session_coordination_performance(self, coordinator, credential_mock):
        """Test performance of session-based credential coordination."""
        session_performance_data = []
        
        # Test coordination for different numbers of sessions
        session_counts = [1, 10, 50, 100]
        
        for session_count in session_counts:
            start_time = time.perf_counter()
            
            # Create multiple sessions concurrently
            coordination_tasks = []
            for i in range(session_count):
                task = coordinator.coordinate_credentials(
                    f"perf_session_{i}", f"perf_test_{session_count}", credential_mock
                )
                coordination_tasks.append(task)
            
            # Execute coordination concurrently
            coordination_results = await asyncio.gather(*coordination_tasks, return_exceptions=True)
            
            end_time = time.perf_counter()
            
            # Analyze results
            successful_coordinations = sum(
                1 for result in coordination_results
                if isinstance(result, dict) and result.get("success")
            )
            
            total_time = end_time - start_time
            throughput = successful_coordinations / total_time if total_time > 0 else 0
            avg_time_per_session = total_time / session_count if session_count > 0 else 0
            
            session_performance_data.append({
                "session_count": session_count,
                "total_time": total_time,
                "successful_coordinations": successful_coordinations,
                "throughput": throughput,
                "avg_time_per_session": avg_time_per_session
            })
            
            # Performance requirements
            assert successful_coordinations >= session_count * 0.95, (
                f"Too many coordination failures for {session_count} sessions: "
                f"{successful_coordinations}/{session_count}"
            )
            
            assert avg_time_per_session < 0.05, (
                f"Coordination too slow for {session_count} sessions: "
                f"{avg_time_per_session:.4f}s per session"
            )
            
            # Cleanup sessions
            for i in range(session_count):
                coordinator.clear_session(f"perf_session_{i}")
        
        # Verify scaling performance
        single_session_throughput = session_performance_data[0]["throughput"]
        
        for data in session_performance_data[1:]:
            current_throughput = data["throughput"]
            session_count = data["session_count"]
            
            # Should maintain reasonable throughput even with more sessions
            throughput_ratio = current_throughput / single_session_throughput
            
            # Allow some degradation but should not be worse than 1/sqrt(session_count)
            min_expected_ratio = 1.0 / (session_count ** 0.3)
            
            assert throughput_ratio >= min_expected_ratio, (
                f"Poor throughput scaling at {session_count} sessions: "
                f"ratio={throughput_ratio:.3f}, expected>={min_expected_ratio:.3f}"
            )
        
        print(f"\nSession Coordination Performance:")
        for data in session_performance_data:
            print(f"Sessions {data['session_count']}: {data['throughput']:.1f} ops/sec, "
                  f"Avg: {data['avg_time_per_session']*1000:.2f}ms/session")
    
    async def test_credential_refresh_performance(self, credential_mock):
        """Test performance of credential refresh operations."""
        # Add OAuth credentials with refresh tokens
        refresh_credentials = []
        
        for i in range(20):
            cred = credential_mock.add_credential(
                "skyfi", f"oauth_refresh_{i}", f"oauth_token_refresh_test_{i}",
                expires_at=time.time() - 1,  # Already expired
                refresh_token=f"refresh_token_{i}",
                scopes=["read:archives", "write:orders"]
            )
            refresh_credentials.append(cred)
        
        # Test refresh performance
        refresh_times = []
        
        for i in range(20):
            start_time = time.perf_counter()
            
            # This should trigger refresh for expired OAuth credential
            injection_result = await credential_mock.inject_credentials(
                request_context={"refresh_test": i},
                required_services={"skyfi"}
            )
            
            end_time = time.perf_counter()
            refresh_times.append(end_time - start_time)
            
            # Should succeed (either through refresh or fallback)
            assert injection_result.success
        
        # Analyze refresh performance
        avg_refresh_time = statistics.mean(refresh_times)
        p95_refresh_time = sorted(refresh_times)[int(0.95 * len(refresh_times))]
        
        # Refresh operations should complete in reasonable time
        assert avg_refresh_time < 0.1, (
            f"Average refresh too slow: {avg_refresh_time:.4f}s"
        )
        assert p95_refresh_time < 0.2, (
            f"P95 refresh too slow: {p95_refresh_time:.4f}s"
        )
        
        print(f"\nCredential Refresh Performance:")
        print(f"Average: {avg_refresh_time*1000:.2f}ms")
        print(f"P95: {p95_refresh_time*1000:.2f}ms")
    
    async def test_large_scale_stress_test(self, credential_mock, coordinator, performance_monitor):
        """Stress test with large scale credential operations."""
        # Large scale test parameters
        NUM_SESSIONS = 200
        NUM_OPERATIONS_PER_SESSION = 10
        
        start_memory = performance_monitor.get_memory_usage()
        start_time = time.perf_counter()
        
        # Create many sessions with multiple operations each
        all_tasks = []
        
        for session_id in range(NUM_SESSIONS):
            for operation_id in range(NUM_OPERATIONS_PER_SESSION):
                task = credential_mock.inject_credentials(
                    request_context={
                        "stress_test": True,
                        "session_id": session_id,
                        "operation_id": operation_id
                    },
                    required_services={"skyfi", "weather"}
                )
                all_tasks.append(task)
        
        # Execute all operations
        print(f"\nExecuting {len(all_tasks)} credential operations...")
        
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        end_memory = performance_monitor.get_memory_usage()
        
        # Analyze stress test results
        total_time = end_time - start_time
        memory_increase = end_memory - start_memory
        
        successful_operations = sum(
            1 for result in results
            if isinstance(result, dict) and result.success
        )
        
        failed_operations = len(results) - successful_operations
        success_rate = successful_operations / len(results)
        throughput = successful_operations / total_time
        
        # Stress test requirements
        assert success_rate >= 0.95, (
            f"Too many failures in stress test: {failed_operations}/{len(results)} "
            f"({success_rate:.2%} success rate)"
        )
        
        assert throughput >= 100, (
            f"Insufficient throughput in stress test: {throughput:.1f} ops/sec"
        )
        
        assert memory_increase < 200, (
            f"Excessive memory usage in stress test: {memory_increase:.2f}MB"
        )
        
        assert total_time < 60, (
            f"Stress test took too long: {total_time:.2f}s"
        )
        
        print(f"Stress Test Results:")
        print(f"Operations: {len(results)}")
        print(f"Success Rate: {success_rate:.2%}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.1f} ops/sec")
        print(f"Memory Increase: {memory_increase:.2f}MB")
        
        # Verify metrics are consistent
        final_metrics = credential_mock.get_injection_metrics()
        
        assert final_metrics["total_injections"] >= successful_operations
        assert final_metrics["successful_injections"] >= successful_operations * 0.95
        
        print(f"Cache Hit Ratio: {final_metrics['credential_cache_hits'] / (final_metrics['credential_cache_hits'] + final_metrics['credential_cache_misses']):.2%}")
        print(f"Average Injection Time: {final_metrics['avg_injection_time_ms']:.2f}ms")
    
    @pytest.mark.parametrize("service_count", [1, 2, 3, 5])
    async def test_multi_service_scaling_performance(self, credential_mock, service_count):
        """Test performance scaling with different numbers of services."""
        # Create service set based on count
        all_services = ["skyfi", "weather", "osm", "service_4", "service_5"]
        required_services = set(all_services[:service_count])
        
        # Add credentials for additional services if needed
        if service_count > 3:
            for i in range(4, service_count + 1):
                service_name = f"service_{i}"
                credential_mock.add_credential(
                    service_name, "api_key", f"test_key_{service_name}",
                    scopes=[f"read:{service_name}"]
                )
        
        # Test injection performance
        injection_times = []
        
        for i in range(50):
            start_time = time.perf_counter()
            
            injection_result = await credential_mock.inject_credentials(
                request_context={"scaling_test": i, "service_count": service_count},
                required_services=required_services
            )
            
            end_time = time.perf_counter()
            injection_times.append(end_time - start_time)
            
            assert injection_result.success
            assert len(injection_result.injected_credentials) >= service_count - 1  # OSM optional
        
        # Analyze scaling performance
        avg_time = statistics.mean(injection_times)
        p95_time = sorted(injection_times)[int(0.95 * len(injection_times))]
        
        # Performance should scale reasonably with service count
        # Allow linear scaling with some overhead
        max_expected_time = 0.005 + (service_count * 0.002)
        
        assert avg_time < max_expected_time, (
            f"Scaling performance poor for {service_count} services: "
            f"{avg_time:.4f}s > {max_expected_time:.4f}s"
        )
        
        print(f"Service Count {service_count}: Avg {avg_time*1000:.2f}ms, P95 {p95_time*1000:.2f}ms")