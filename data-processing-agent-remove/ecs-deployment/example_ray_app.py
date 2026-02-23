#!/usr/bin/env python3
"""Example Ray application to test the ECS cluster"""

import ray
import time
import sys

if len(sys.argv) < 2:
    print("Usage: python example_ray_app.py <HEAD_NODE_PUBLIC_IP>")
    sys.exit(1)

head_ip = sys.argv[1]

# Connect to Ray cluster
print(f"Connecting to Ray cluster at {head_ip}...")
ray.init(f"ray://{head_ip}:10001")

print(f"Ray cluster resources: {ray.cluster_resources()}")
print(f"Available nodes: {len(ray.nodes())}")

# Simple remote function
@ray.remote
def compute_task(x):
    time.sleep(1)
    return x * x

# Submit tasks
print("\nSubmitting 10 tasks...")
start_time = time.time()
results = ray.get([compute_task.remote(i) for i in range(10)])
elapsed = time.time() - start_time
print(f"Results: {results}")
print(f"Completed in {elapsed:.2f} seconds")

# Remote class (Actor)
@ray.remote
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
        return self.count
    
    def get_count(self):
        return self.count

# Create actor
print("\nTesting Ray actor...")
counter = Counter.remote()
print(f"Count: {ray.get(counter.increment.remote())}")
print(f"Count: {ray.get(counter.increment.remote())}")
print(f"Count: {ray.get(counter.increment.remote())}")

# Parallel computation
@ray.remote
def monte_carlo_pi(num_samples):
    import random
    inside = 0
    for _ in range(num_samples):
        x, y = random.random(), random.random()
        if x*x + y*y <= 1:
            inside += 1
    return inside

print("\nEstimating Pi using Monte Carlo method...")
num_tasks = 10
samples_per_task = 1000000
start_time = time.time()
results = ray.get([monte_carlo_pi.remote(samples_per_task) for _ in range(num_tasks)])
pi_estimate = 4 * sum(results) / (num_tasks * samples_per_task)
elapsed = time.time() - start_time
print(f"Pi estimate: {pi_estimate}")
print(f"Completed in {elapsed:.2f} seconds")

print("\nRay application completed successfully!")
print(f"Total nodes in cluster: {len(ray.nodes())}")
ray.shutdown()
