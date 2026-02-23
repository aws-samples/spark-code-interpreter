#!/usr/bin/env python3
"""Example Ray application to test the cluster"""

import ray
import time

# Connect to Ray cluster
# Make sure to port-forward first:
# kubectl port-forward -n ray-system service/ray-cluster-head-svc 10001:10001

ray.init("ray://localhost:10001")

print(f"Ray cluster resources: {ray.cluster_resources()}")

# Simple remote function
@ray.remote
def compute_task(x):
    time.sleep(1)
    return x * x

# Submit tasks
print("\nSubmitting 10 tasks...")
results = ray.get([compute_task.remote(i) for i in range(10)])
print(f"Results: {results}")

# Remote class (Actor)
@ray.remote
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
        return self.count

# Create actor
print("\nTesting Ray actor...")
counter = Counter.remote()
print(f"Count: {ray.get(counter.increment.remote())}")
print(f"Count: {ray.get(counter.increment.remote())}")

print("\nRay application completed successfully!")
ray.shutdown()
