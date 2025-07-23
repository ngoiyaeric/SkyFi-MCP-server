"""
Performance Benchmarks and Load Testing

This module provides comprehensive performance testing for the SkyFi MCP server,
including benchmarks, load testing, and resource usage monitoring.
"""

from __future__ import annotations

import asyncio
import statistics
import time
import pytest
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmarks and load testing suite."""
    
    async def test_authentication_performance(self, test_client, auth_headers, performance_monitor):
        """Benchmark authentication method performance."""
        auth_methods = {
            "api_key": auth_headers["valid_api_key"],
            "oauth": auth_headers["valid_oauth"], 
            "pat": auth_headers["valid_pat"]
        }
        
        benchmark_results = {}
        
        for method, headers in auth_methods.items():
            performance_monitor.start_monitoring(f"auth_{method}")
            
            # Warm up
            for _ in range(10):
                await test_client.get("/skyfi/search-archives", headers=headers)
                
            # Benchmark
            times = []
            iterations = 1000
            
            for _ in range(iterations):
                start = time.perf_counter()
                response = await test_client.get("/skyfi/search-archives", headers=headers)
                end = time.perf_counter()
                
                times.append(end - start)
                
                # Ensure we got a valid auth response (even if business logic fails)
                assert response.status_code != 401, f"Auth failed for method {method}"
                
            metrics = performance_monitor.stop_monitoring(f"auth_{method}")
            
            benchmark_results[method] = {
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "p50_time": statistics.median(times),
                "p95_time": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                "p99_time": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times),
                "memory_delta_mb": metrics["memory_delta"] if metrics else 0
            }
            
        # Performance assertions
        for method, results in benchmark_results.items():
            # Authentication should be sub-millisecond on average
            assert results["avg_time"] < 0.001, (
                f"{method} auth too slow: {results['avg_time']:.4f}s average"
            )
            
            # 95th percentile should be under 5ms
            assert results["p95_time"] < 0.005, (
                f"{method} p95 too slow: {results['p95_time']:.4f}s"
            )
            
            # Memory usage should be minimal
            assert results["memory_delta_mb"] < 1.0, (
                f"{method} auth used too much memory: {results['memory_delta_mb']:.2f}MB"
            )
            
        print(f"\nAuthentication Performance Results:")
        for method, results in benchmark_results.items():
            print(f"{method:10} | Avg: {results['avg_time']*1000:6.2f}ms | "
                  f"P95: {results['p95_time']*1000:6.2f}ms | "
                  f"P99: {results['p99_time']*1000:6.2f}ms")
                  
    async def test_tool_execution_performance(self, test_client, auth_headers, benchmark_data):
        """Benchmark tool execution performance."""
        headers = auth_headers["valid_api_key"]
        
        # Test different request sizes
        request_sizes = {
            "small": benchmark_data["small_request"],
            "medium": benchmark_data["medium_request"], 
            "large": benchmark_data["large_request"]
        }
        
        benchmark_results = {}
        
        for size_name, request_data in request_sizes.items():
            times = []
            iterations = 50  # Fewer iterations for larger requests
            
            # Warm up
            for _ in range(5):
                await test_client.post("/skyfi/search-archives", json=request_data, headers=headers)
                
            # Benchmark
            for _ in range(iterations):
                start = time.perf_counter()
                response = await test_client.post("/skyfi/search-archives", json=request_data, headers=headers)
                end = time.perf_counter()
                
                times.append(end - start)
                
                # Ensure request was processed
                assert response.status_code in [200, 422], f"Unexpected status for {size_name}: {response.status_code}"
                
            benchmark_results[size_name] = {
                "avg_time": statistics.mean(times),
                "p95_time": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                "max_time": max(times)
            }
            
        # Performance assertions based on request complexity
        assert benchmark_results["small"]["avg_time"] < 0.5, (
            f"Small requests too slow: {benchmark_results['small']['avg_time']:.3f}s"
        )
        assert benchmark_results["medium"]["avg_time"] < 1.0, (
            f"Medium requests too slow: {benchmark_results['medium']['avg_time']:.3f}s"
        )
        assert benchmark_results["large"]["avg_time"] < 2.0, (
            f"Large requests too slow: {benchmark_results['large']['avg_time']:.3f}s"
        )
        
        print(f"\nTool Execution Performance Results:")
        for size, results in benchmark_results.items():
            print(f"{size:6} | Avg: {results['avg_time']*1000:7.1f}ms | "
                  f"P95: {results['p95_time']*1000:7.1f}ms | "
                  f"Max: {results['max_time']*1000:7.1f}ms")
                  
    async def test_concurrent_request_performance(self, test_client, auth_headers, performance_config):
        """Test server performance under concurrent load."""
        headers = auth_headers["valid_api_key"]
        concurrent_users = performance_config["concurrent_users"]
        requests_per_user = performance_config["requests_per_user"]
        
        async def user_simulation(user_id: int):
            """Simulate a user making multiple requests."""
            user_times = []
            
            for request_num in range(requests_per_user):
                start_time = time.perf_counter()
                
                try:
                    response = await test_client.get(
                        "/skyfi/search-archives",
                        headers={**headers, "X-User-ID": f"load-test-{user_id}"}
                    )
                    end_time = time.perf_counter()
                    
                    user_times.append(end_time - start_time)
                    
                    # Verify response is valid
                    assert response.status_code in [200, 401, 422, 429], (
                        f"Unexpected status {response.status_code} for user {user_id}"
                    )
                    
                except Exception as e:
                    print(f"User {user_id} request {request_num} failed: {e}")
                    # Continue with other requests
                    
            return user_times
            
        # Run concurrent user simulations
        print(f"Starting load test: {concurrent_users} users, {requests_per_user} requests each")
        
        start_time = time.perf_counter()
        tasks = [user_simulation(i) for i in range(concurrent_users)]
        all_user_times = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        # Flatten all response times
        all_times = [time_val for user_times in all_user_times for time_val in user_times]
        
        if not all_times:
            pytest.fail("No successful requests in load test")
            
        # Calculate performance metrics
        total_requests = len(all_times)
        total_duration = end_time - start_time
        requests_per_second = total_requests / total_duration
        
        performance_metrics = {
            "total_requests": total_requests,
            "total_duration": total_duration,
            "requests_per_second": requests_per_second,
            "avg_response_time": statistics.mean(all_times),
            "p50_response_time": statistics.median(all_times),
            "p95_response_time": statistics.quantiles(all_times, n=20)[18],
            "p99_response_time": statistics.quantiles(all_times, n=100)[98],
            "max_response_time": max(all_times),
            "min_response_time": min(all_times)
        }
        
        # Performance assertions
        assert performance_metrics["avg_response_time"] < performance_config["max_response_time"], (
            f"Average response time too high: {performance_metrics['avg_response_time']:.3f}s"
        )
        
        assert performance_metrics["p95_response_time"] < performance_config["max_p95_response_time"], (
            f"95th percentile too high: {performance_metrics['p95_response_time']:.3f}s"
        )
        
        assert performance_metrics["requests_per_second"] > 10, (
            f"Throughput too low: {performance_metrics['requests_per_second']:.1f} req/s"
        )
        
        print(f"\nConcurrent Load Test Results:")
        print(f"Total requests: {performance_metrics['total_requests']:,}")
        print(f"Duration: {performance_metrics['total_duration']:.2f}s")
        print(f"Throughput: {performance_metrics['requests_per_second']:.1f} req/s")
        print(f"Response times - Avg: {performance_metrics['avg_response_time']*1000:.1f}ms | "
              f"P95: {performance_metrics['p95_response_time']*1000:.1f}ms | "
              f"P99: {performance_metrics['p99_response_time']*1000:.1f}ms")
              
    async def test_memory_usage_under_load(self, test_client, auth_headers, performance_config):
        """Test memory usage and leak detection under sustained load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        headers = auth_headers["valid_api_key"]
        
        # Record initial memory
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_samples = [initial_memory]
        
        # Generate sustained load in batches
        batch_size = 50
        num_batches = 10
        
        for batch_num in range(num_batches):
            print(f"Running batch {batch_num + 1}/{num_batches}")
            
            # Create batch of concurrent requests
            tasks = []
            for i in range(batch_size):
                task = test_client.get("/skyfi/search-archives", headers=headers)
                tasks.append(task)
                
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sample memory usage
            current_memory = process.memory_info().rss / (1024 * 1024)  # MB
            memory_samples.append(current_memory)
            
            print(f"Memory after batch {batch_num + 1}: {current_memory:.1f}MB")
            
            # Brief pause to allow garbage collection
            await asyncio.sleep(0.1)
            
        # Analyze memory usage
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        memory_growth = final_memory - initial_memory
        
        # Memory assertions
        assert memory_growth < performance_config["max_memory_usage_mb"], (
            f"Memory usage grew too much: {memory_growth:.1f}MB "
            f"(from {initial_memory:.1f}MB to {final_memory:.1f}MB)"
        )
        
        # Check for memory leaks (steady growth)
        if len(memory_samples) >= 5:
            # Calculate trend - memory should stabilize
            recent_samples = memory_samples[-5:]
            memory_trend = (recent_samples[-1] - recent_samples[0]) / len(recent_samples)
            
            assert memory_trend < 10.0, (  # Less than 10MB growth per batch in recent samples
                f"Potential memory leak detected: {memory_trend:.1f}MB/batch growth trend"
            )
            
        print(f"\nMemory Usage Results:")
        print(f"Initial: {initial_memory:.1f}MB")
        print(f"Final: {final_memory:.1f}MB") 
        print(f"Peak: {max_memory:.1f}MB")
        print(f"Growth: {memory_growth:.1f}MB")
        
    async def test_database_performance(self, test_client, auth_headers):
        """Test database operation performance (if applicable)."""
        # This would test database query performance for operations like
        # user lookups, token validation, etc.
        
        headers = auth_headers["valid_api_key"]
        db_operation_times = []
        
        # Test repeated authentication (database lookups)
        iterations = 200
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            response = await test_client.get("/skyfi/search-archives", headers=headers)
            
            end_time = time.perf_counter()
            db_operation_times.append(end_time - start_time)
            
            # Ensure we're testing database operations
            assert response.status_code in [200, 401, 422]
            
        # Analyze database performance
        avg_db_time = statistics.mean(db_operation_times)
        p95_db_time = statistics.quantiles(db_operation_times, n=20)[18]
        
        # Database operations should be fast
        assert avg_db_time < 0.1, f"Database operations too slow: {avg_db_time:.3f}s average"
        assert p95_db_time < 0.2, f"Database p95 too slow: {p95_db_time:.3f}s"
        
        print(f"\nDatabase Performance Results:")
        print(f"Average: {avg_db_time*1000:.1f}ms")
        print(f"P95: {p95_db_time*1000:.1f}ms")
        
    async def test_external_api_timeout_handling(self, test_client, auth_headers):
        """Test performance when external APIs are slow/timeout."""
        headers = auth_headers["valid_api_key"]
        
        # Test with request that would hit external APIs
        request_data = {
            "aoi": {
                "type": "Point",
                "coordinates": [-122.4194, 37.7749]
            },
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
        
        timeout_scenarios = []
        
        for _ in range(10):
            start_time = time.perf_counter()
            
            try:
                response = await test_client.post(
                    "/skyfi/search-archives", 
                    json=request_data,
                    headers=headers,
                    timeout=30.0  # 30 second timeout
                )
                
                end_time = time.perf_counter()
                response_time = end_time - start_time
                
                timeout_scenarios.append({
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "success": response.status_code < 500
                })
                
            except Exception as e:
                end_time = time.perf_counter() 
                timeout_scenarios.append({
                    "response_time": end_time - start_time,
                    "status_code": 500,
                    "success": False,
                    "error": str(e)
                })
                
        # Analyze timeout handling
        successful_requests = [s for s in timeout_scenarios if s["success"]]
        failed_requests = [s for s in timeout_scenarios if not s["success"]]
        
        if successful_requests:
            avg_success_time = statistics.mean([s["response_time"] for s in successful_requests])
            print(f"Average successful request time: {avg_success_time:.2f}s")
            
        if failed_requests:
            avg_failure_time = statistics.mean([s["response_time"] for s in failed_requests])
            print(f"Average failed request time: {avg_failure_time:.2f}s")
            
        # Timeouts should be handled gracefully and within reasonable time
        max_response_time = max([s["response_time"] for s in timeout_scenarios])
        assert max_response_time < 31.0, f"Request took too long even with timeout: {max_response_time:.2f}s"