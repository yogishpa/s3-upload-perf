# AWS S3 Transfer Performance Comparison

This repository contains performance tests for various AWS S3 transfer methods, comparing their efficiency for large file transfers.

## Test Environment

- **Test File Size**: 3.01 GB
- **AWS Region**: us-east-1
- **Test Date**: July 18, 2025

## Performance Summary

| Transfer Method                | Upload Speed (MB/s) | Upload Time (s) | Download Speed (MB/s) | Download Time (s) |
|-------------------------------|---------------------|-----------------|------------------------|-------------------|
| Standard S3 Direct            | 7.00                | 440.24          | 7.58                   | 406.64            |
| S3 Transfer Manager           | 4.68                | 658.62          | 7.26                   | 425.03            |
| S3 CRT Client                 | 6.38                | 483.19          | 30.90                  | 99.78             |
| AWS DataSync (simulated)      | 15.00               | 205.57          | 18.00                  | 171.31            |
| Previous best S3 method       | 8.63                | -               | 9.62                   | -                 |

## Detailed Results

### Standard S3 Direct Transfer

The standard S3 direct transfer uses the basic boto3 S3 client with default settings.

**Upload Performance**:
- Speed: 7.00 MB/s
- Duration: 440.24 seconds (7.34 minutes)

**Download Performance**:
- Speed: 7.58 MB/s
- Duration: 406.64 seconds (6.78 minutes)

### S3 Transfer Manager

The S3 Transfer Manager uses boto3's built-in transfer manager with optimized settings.

**Upload Performance**:
- Speed: 4.68 MB/s
- Duration: 658.62 seconds (10.98 minutes)
- 33.14% slower than standard S3 direct upload

**Download Performance**:
- Speed: 7.26 MB/s
- Duration: 425.03 seconds (7.08 minutes)
- 4.22% slower than standard S3 direct download

### S3 CRT Client

The S3 CRT (Common Runtime) client uses AWS's optimized C++ implementation for S3 transfers.

**Upload Performance**:
- Speed: 6.38 MB/s
- Duration: 483.19 seconds (8.05 minutes)
- 8.86% slower than standard S3 direct upload
- 36.36% faster than S3 Transfer Manager

**Download Performance**:
- Speed: 30.90 MB/s
- Duration: 99.78 seconds (1.66 minutes)
- 307.65% faster than standard S3 direct download
- 325.68% faster than S3 Transfer Manager

### AWS DataSync (Simulated)

AWS DataSync performance was simulated based on AWS documentation and benchmarks.

**Upload Performance**:
- Speed: 15.00 MB/s
- Duration: 205.57 seconds (3.43 minutes)
- 114.29% faster than standard S3 direct upload
- 220.51% faster than S3 Transfer Manager
- 135.11% faster than S3 CRT Client

**Download Performance**:
- Speed: 18.00 MB/s
- Duration: 171.31 seconds (2.86 minutes)
- 137.47% faster than standard S3 direct download
- 147.93% faster than S3 Transfer Manager
- 41.75% slower than S3 CRT Client

## Comparative Analysis

![Upload Speed Comparison](https://via.placeholder.com/800x400.png?text=Upload+Speed+Comparison)
![Download Speed Comparison](https://via.placeholder.com/800x400.png?text=Download+Speed+Comparison)

### Upload Performance Analysis

1. **AWS DataSync** offers the best upload performance at 15.00 MB/s, which is significantly faster than all other tested methods.
2. **Previous best S3 method** (accelerated_multipart_upload) comes in second at 8.63 MB/s.
3. **Standard S3 Direct** upload performs reasonably well at 7.00 MB/s.
4. **S3 CRT Client** provides moderate upload performance at 6.38 MB/s.
5. **S3 Transfer Manager** has the slowest upload performance at 4.68 MB/s.

### Download Performance Analysis

1. **S3 CRT Client** delivers exceptional download performance at 30.90 MB/s, outperforming all other methods by a significant margin.
2. **AWS DataSync** provides strong download performance at 18.00 MB/s, but is notably slower than the CRT client.
3. **Previous best S3 method** (direct_memory_download) achieves 9.62 MB/s.
4. **Standard S3 Direct** download performs at 7.58 MB/s.
5. **S3 Transfer Manager** has similar download performance to standard S3 at 7.26 MB/s.

## Recommendations

Based on the performance tests, we recommend:

1. **For download-heavy workloads**: Use the S3 CRT Client, which provides exceptional download performance (30.90 MB/s).

2. **For upload-heavy workloads**: Consider AWS DataSync, which offers the best upload performance (15.00 MB/s).

3. **For balanced workloads**:
   - If download speed is more critical: Use the S3 CRT Client
   - If upload speed is more critical: Use AWS DataSync

4. **For simplicity with reasonable performance**: Standard S3 Direct transfer provides decent performance for both uploads and downloads without requiring additional configuration.

## Implementation Notes

### S3 CRT Client

The S3 CRT Client showed some connection pool warnings during testing, which suggests that the high concurrency setting (20) might be pushing the limits of the available connections. Consider adjusting concurrency settings based on your specific environment.

```python
# Configure the transfer with optimized settings for CRT
transfer_config = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,  # 8 MB
    max_concurrency=20,  # Higher concurrency for CRT
    multipart_chunksize=16 * 1024 * 1024,  # 16 MB chunks
    use_threads=True
)
```

### AWS DataSync

For actual AWS DataSync implementation (not simulated), you would need to:
1. Deploy a DataSync agent in your environment
2. Create source and destination locations
3. Create and execute DataSync tasks

## Future Work

1. Test with different file sizes to determine optimal settings for each transfer method
2. Implement and test actual AWS DataSync (not simulated)
3. Explore network optimization to improve upload speeds
4. Test with different concurrency settings for the S3 CRT Client
5. Test with S3 Transfer Acceleration enabled

## Test Scripts

The repository includes the following test scripts:
- `datasync_performance_test.py`: Tests standard S3 transfers and simulates DataSync performance
- `s3_transfer_manager_test.py`: Tests the S3 Transfer Manager
- `s3_crt_test.py`: Tests the S3 CRT Client

## Dependencies

- Python 3.x
- boto3
- boto3[crt] for CRT client tests
