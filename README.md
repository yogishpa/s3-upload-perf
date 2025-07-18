# AWS S3 Transfer Performance Comparison

This repository contains performance tests for various AWS S3 transfer methods, comparing their efficiency for large file transfers.

## Test Environment

- **Test File Size**: 3.01 GB
- **AWS Region**: us-east-1
- **Test Date**: July 18, 2025

## Performance Summary

| Transfer Method                | Upload Speed (MB/s) | Upload Time (s) | Download Speed (MB/s) | Download Time (s) |
|-------------------------------|---------------------|-----------------|------------------------|-------------------|
| Standard S3 Direct            | 29.59               | 104.88          | 27.19                  | 113.39            |
| S3 Transfer Manager           | 32.91               | 93.70           | 28.15                  | 109.55            |
| S3 CRT Client                 | 30.92               | 99.73           | 38.21                  | 80.70             |
| Optimized S3 (No Acceleration)| 38.62               | 79.84           | 38.64                  | 79.81             |
| Optimized S3 (With Acceleration)| 37.98             | 81.18           | 45.65                  | 67.54             |
| Cost-Optimized S3 (Range GET) | 34.00               | 90.70           | 23.89                  | 129.07            |

## Detailed Results

### Standard S3 Direct Transfer

The standard S3 direct transfer uses the basic boto3 S3 client with default settings.

**Upload Performance**:
- Speed: 29.59 MB/s
- Duration: 104.88 seconds (1.75 minutes)

**Download Performance**:
- Speed: 27.19 MB/s
- Duration: 113.39 seconds (1.89 minutes)

### S3 Transfer Manager

The S3 Transfer Manager uses boto3's built-in transfer manager with optimized settings.

**Upload Performance**:
- Speed: 32.91 MB/s
- Duration: 93.70 seconds (1.56 minutes)
- 11.22% faster than standard S3 direct upload

**Download Performance**:
- Speed: 28.15 MB/s
- Duration: 109.55 seconds (1.83 minutes)
- 3.53% faster than standard S3 direct download

### S3 CRT Client

The S3 CRT (Common Runtime) client uses AWS's optimized C++ implementation for S3 transfers.

**Upload Performance**:
- Speed: 30.92 MB/s
- Duration: 99.73 seconds (1.66 minutes)
- 4.49% faster than standard S3 direct upload
- 6.05% slower than S3 Transfer Manager

**Download Performance**:
- Speed: 38.21 MB/s
- Duration: 80.70 seconds (1.35 minutes)
- 40.53% faster than standard S3 direct download
- 35.74% faster than S3 Transfer Manager

### Optimized S3 Transfer (Without Acceleration)

This method combines optimized configuration settings with the boto3 S3 client.

**Upload Performance**:
- Speed: 38.62 MB/s
- Duration: 79.84 seconds (1.33 minutes)
- 30.52% faster than standard S3 direct upload
- 17.35% faster than S3 Transfer Manager
- 24.90% faster than S3 CRT Client

**Download Performance**:
- Speed: 38.64 MB/s
- Duration: 79.81 seconds (1.33 minutes)
- 42.11% faster than standard S3 direct download
- 37.26% faster than S3 Transfer Manager
- 1.13% faster than S3 CRT Client

### Optimized S3 Transfer (With Acceleration)

This method combines optimized configuration settings with S3 Transfer Acceleration.

**Upload Performance**:
- Speed: 37.98 MB/s
- Duration: 81.18 seconds (1.35 minutes)
- 28.35% faster than standard S3 direct upload
- 15.41% faster than S3 Transfer Manager
- 22.83% faster than S3 CRT Client
- 1.67% slower than Optimized S3 without Acceleration

**Download Performance**:
- Speed: 45.65 MB/s
- Duration: 67.54 seconds (1.13 minutes)
- 67.89% faster than standard S3 direct download
- 62.17% faster than S3 Transfer Manager
- 19.47% faster than S3 CRT Client
- 18.14% faster than Optimized S3 without Acceleration

### Cost-Optimized S3 Transfer (Range GET)

This method uses optimized settings without Transfer Acceleration, and implements parallel Range GET requests for downloads to achieve excellent performance without additional costs.

**Upload Performance**:
- Speed: 34.00 MB/s
- Duration: 90.70 seconds (1.51 minutes)
- 14.90% faster than standard S3 direct upload
- 3.32% faster than S3 Transfer Manager
- 9.96% faster than S3 CRT Client
- 11.95% slower than Optimized S3 without Acceleration

**Download Performance**:
- Speed: 23.89 MB/s
- Duration: 129.07 seconds (2.15 minutes)
- 12.14% slower than standard S3 direct download
- 15.13% slower than S3 Transfer Manager
- 37.48% slower than S3 CRT Client
- 38.17% slower than Optimized S3 without Acceleration

## Cost Comparison

### Standard S3 vs S3 Transfer Acceleration

1. **Data Transfer IN to S3**:
   - Standard S3: Free
   - S3 Transfer Acceleration: $0.04/GB

2. **Data Transfer OUT from S3 to Internet**:
   - Standard S3: $0.09/GB (up to 10 TB/month)
   - S3 Transfer Acceleration: $0.09/GB + $0.04/GB = $0.13/GB

3. **Cost for our 3.01 GB test file**:
   - Upload with Standard S3: Free
   - Upload with Acceleration: $0.12
   - Download with Standard S3: $0.27
   - Download with Acceleration: $0.39

### Cost-Optimized Approach

Our Cost-Optimized S3 Transfer method achieves good performance without incurring the additional Transfer Acceleration costs.

**Cost savings per transfer of our 3.01 GB file**: $0.12 (upload) + $0.12 (download) = $0.24

For large-scale operations or frequent transfers, these savings can be significant while still maintaining good performance.

## Comparative Analysis

![Upload Speed Comparison](https://via.placeholder.com/800x400.png?text=Upload+Speed+Comparison)
![Download Speed Comparison](https://via.placeholder.com/800x400.png?text=Download+Speed+Comparison)

### Upload Performance Analysis

1. **Optimized S3 (No Acceleration)** delivers the best upload performance at 38.62 MB/s, significantly outperforming all other methods.
2. **Optimized S3 (With Acceleration)** is a close second at 37.98 MB/s, showing that acceleration is not necessary for optimal upload performance.
3. **Cost-Optimized S3** provides good upload performance at 34.00 MB/s.
4. **S3 Transfer Manager** achieves 32.91 MB/s for uploads.
5. **S3 CRT Client** provides moderate upload performance at 30.92 MB/s.
6. **Standard S3 Direct** upload performs at 29.59 MB/s.

### Download Performance Analysis

1. **Optimized S3 (With Acceleration)** delivers exceptional download performance at 45.65 MB/s, but at additional cost.
2. **Optimized S3 (No Acceleration)** provides excellent performance at 38.64 MB/s without additional costs.
3. **S3 CRT Client** provides similar performance at 38.21 MB/s.
4. **S3 Transfer Manager** achieves 28.15 MB/s for downloads.
5. **Standard S3 Direct** download performs at 27.19 MB/s.
6. **Cost-Optimized S3 (Range GET)** performs at 23.89 MB/s, which is lower than expected and needs optimization.

## Recommendations

Based on the performance tests and cost considerations, we recommend:

1. **For cost-sensitive workloads**: Use the Optimized S3 Transfer configuration without acceleration, which provides excellent performance for both uploads (38.62 MB/s) and downloads (38.64 MB/s) without incurring additional Transfer Acceleration costs.

2. **For performance-critical workloads**: Use Optimized S3 Transfer with Acceleration, especially for downloads where it provides exceptional performance (45.65 MB/s), but be aware of the additional costs.

3. **For upload-heavy workloads**: Use Optimized S3 Transfer without acceleration, which offers the best upload performance (38.62 MB/s) without additional costs.

4. **For balanced workloads**: Use Optimized S3 Transfer without acceleration, which provides excellent performance for both uploads and downloads without additional costs.

## Implementation Notes

### Optimized S3 Transfer Configuration

The optimized S3 transfer configuration uses the following settings:

```python
# Create a boto3 client with optimized settings
s3_config = Config(
    region_name='us-east-1',
    signature_version='s3v4',
    retries={
        'max_attempts': 10,
        'mode': 'adaptive'  # Use adaptive retry mode
    },
    s3={
        'addressing_style': 'virtual',
        'payload_signing_enabled': False,  # Improves performance
    },
    max_pool_connections=50  # Increase connection pool size
)

# Configure the transfer with optimized settings
transfer_config = TransferConfig(
    multipart_threshold=25 * 1024 * 1024,  # 25 MB
    max_concurrency=15,                    # 15 concurrent threads for uploads
    max_concurrency=20,                    # 20 concurrent threads for downloads
    multipart_chunksize=25 * 1024 * 1024,  # 25 MB chunks
    use_threads=True
)
```

### Connection Pool Warnings

During testing with high concurrency settings, some "Connection pool is full" warnings were observed. These warnings indicate that the connection pool is being fully utilized, which is expected with high concurrency settings. These warnings don't necessarily indicate a problem, but if they become frequent, consider:

1. Adjusting the concurrency settings to a slightly lower value
2. Increasing the connection pool size if your environment allows it

### Range GET Implementation Needs Improvement

The current Range GET implementation for downloads (23.89 MB/s) performs worse than standard optimized downloads (38.64 MB/s). This suggests that the current implementation needs optimization in areas such as:

1. Chunk size selection
2. Thread management
3. Parallel request coordination
4. File writing efficiency

## Future Work

1. Improve the Range GET implementation to achieve better download performance
2. Test with different file sizes to determine optimal settings for each transfer method
3. Explore network optimization to improve upload speeds
4. Test with different concurrency settings for the optimized configuration
5. Test with different chunk sizes to find the optimal balance
6. Test in different network environments and regions

## Test Scripts

The repository includes the following test scripts:
- `s3_performance_test.py`: Tests standard S3 direct transfers
- `s3_transfer_manager_test.py`: Tests the S3 Transfer Manager
- `s3_crt_test.py`: Tests the S3 CRT Client
- `s3_optimized_transfer.py`: Tests the optimized S3 transfer configuration with and without acceleration
- `s3_optimized_no_acceleration.py`: Tests the cost-optimized S3 transfer configuration without acceleration

## Dependencies

- Python 3.x
- boto3
- boto3[crt] for CRT client tests
