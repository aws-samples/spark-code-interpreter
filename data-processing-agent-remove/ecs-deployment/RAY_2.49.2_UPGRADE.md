# Ray 2.49.2 Upgrade with ML Packages

## Changes

### Ray Version
- **Previous**: Ray 2.42.0
- **New**: Ray 2.49.2

### Python Packages Added
- `torch` - PyTorch for machine learning
- `torchvision` - Computer vision models and utilities
- `numpy` - Numerical computing
- `filelock` - File locking utilities
- `awswrangler>=3.0.0` - AWS data processing (existing)
- `pyarrow>=10.0.0` - Parquet file support (existing)
- `pyathena>=3.0.0` - Athena database connections (existing)

## Deployment Steps

### 1. Cleanup Existing Cluster
```bash
cd ecs-deployment
python3 cleanup.py
```

### 2. Deploy New Cluster
```bash
python3 deploy.py
```

The deployment will:
- Use Ray 2.49.2 Docker image
- Install all Python packages at container startup
- Configure head node and workers with same packages

### 3. Verify Deployment
```bash
# Get head node IP
python3 get_head_ip.py

# Test Ray cluster
python3 test_ray_data.py
```

### 4. Update Backend Configuration
Update `backend/.env` with new head node IP if changed:
```
RAY_HEAD_IP=<new-ip>
```

## Package Installation

Packages are installed at container startup using:
```bash
pip install torch filelock numpy torchvision awswrangler>=3.0.0 pyarrow>=10.0.0 pyathena>=3.0.0
```

This happens before Ray starts, ensuring all packages are available for job execution.

## Configuration Files Updated

1. **config.yaml**
   - Updated `ray_version: "2.49.2"` for head and worker
   - Added `python_packages` list (documentation)

2. **deploy.py**
   - Modified head node command to install packages
   - Modified worker node command to install packages
   - Uses `entryPoint: ["/bin/bash", "-c"]` for shell execution

3. **ray-cluster-requirements.txt**
   - Documented all installed packages

## Startup Time

Note: Container startup will take longer (~2-3 minutes) due to package installation.
This is a one-time cost per container launch.

## Alternative: Custom Docker Image

For faster startup, consider building a custom Docker image:

```dockerfile
FROM rayproject/ray:2.49.2
RUN pip install torch filelock numpy torchvision awswrangler>=3.0.0 pyarrow>=10.0.0 pyathena>=3.0.0
```

Then update `deploy.py` to use the custom image instead of runtime installation.

## Verification

After deployment, verify packages are installed:

```python
import ray
ray.init(address='auto')

@ray.remote
def check_packages():
    import torch
    import torchvision
    import numpy
    import filelock
    import awswrangler
    return {
        'torch': torch.__version__,
        'torchvision': torchvision.__version__,
        'numpy': numpy.__version__
    }

result = ray.get(check_packages.remote())
print(result)
```

## Rollback

To rollback to Ray 2.42.0:
1. Update `config.yaml` ray_version to "2.42.0"
2. Remove torch/torchvision/filelock from deploy.py commands
3. Run `python3 cleanup.py && python3 deploy.py`
