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
| Optimized S3 (No Acceleration)| 35.42               | 87.06           | 31.64                  | 97.45             |
| Optimized S3 (With Acceleration)| 34.60             | 89.11           | 48.67                  | 63.35             |

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

### Optimized S3 Transfer (Without Acceleration)

This method combines optimized configuration settings with the boto3 S3 client.

**Upload Performance**:
- Speed: 35.42 MB/s
- Duration: 87.06 seconds (1.45 minutes)
- 405.99% faster than standard S3 direct upload
- 455.16% faster than S3 CRT Client

**Download Performance**:
- Speed: 31.64 MB/s
- Duration: 97.45 seconds (1.62 minutes)
- 317.47% faster than standard S3 direct download
- 2.41% faster than S3 CRT Client

### Optimized S3 Transfer (With Acceleration)

This method combines optimized configuration settings with S3 Transfer Acceleration.

**Upload Performance**:
- Speed: 34.60 MB/s
- Duration: 89.11 seconds (1.49 minutes)
- 394.33% faster than standard S3 direct upload
- 442.37% faster than S3 CRT Client

**Download Performance**:
- Speed: 48.67 MB/s
- Duration: 63.35 seconds (1.06 minutes)
- 542.14% faster than standard S3 direct download
- 57.52% faster than S3 CRT Client

## Comparative Analysis

![Upload Speed Comparison](https://via.placeholder.com/800x400.png?text=Upload+Speed+Comparison)
![Download Speed Comparison](https://via.placeholder.com/800x400.png?text=Download+Speed+Comparison)

### Upload Performance Analysis

1. **Optimized S3 (No Acceleration)** delivers the best upload performance at 35.42 MB/s, significantly outperforming all other methods.
2. **Optimized S3 (With Acceleration)** is a close second at 34.60 MB/s, showing that local network conditions may sometimes make acceleration unnecessary.
3. **Standard S3 Direct** upload performs at 7.00 MB/s.
4. **S3 CRT Client** provides moderate upload performance at 6.38 MB/s.
5. **S3 Transfer Manager** has the slowest upload performance at 4.68 MB/s.

### Download Performance Analysis

1. **Optimized S3 (With Acceleration)** delivers exceptional download performance at 48.67 MB/s, outperforming all other methods.
2. **Optimized S3 (No Acceleration)** and **S3 CRT Client** provide similar performance at 31.64 MB/s and 30.90 MB/s respectively.
3. **Standard S3 Direct** download performs at 7.58 MB/s.
4. **S3 Transfer Manager** has similar download performance to standard S3 at 7.26 MB/s.

## Recommendations

Based on the performance tests, we recommend:

1. **For all workloads**: Use the Optimized S3 Transfer configuration, which provides the best overall performance for both uploads and downloads.
   - For downloads, enable S3 Transfer Acceleration for an additional 54% speed improvement
   - For uploads, acceleration may not provide significant benefits in all network environments

2. **For download-heavy workloads**: Use Optimized S3 Transfer with Acceleration, which provides exceptional download performance (48.67 MB/s).

3. **For upload-heavy workloads**: Use Optimized S3 Transfer without Acceleration, which offers the best upload performance (35.42 MB/s).

4. **For balanced workloads**: Use Optimized S3 Transfer with Acceleration, which provides excellent performance for both uploads (34.60 MB/s) and downloads (48.67 MB/s).

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
        'use_accelerate_endpoint': True,  # Enable Transfer Acceleration
        'addressing_style': 'virtual',
        'payload_signing_enabled': False,
    }
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

## Future Work

1. Test with different file sizes to determine optimal settings for each transfer method
2. Explore network optimization to improve upload speeds
3. Test with different concurrency settings for the optimized configuration
4. Test with different chunk sizes to find the optimal balance
5. Test in different network environments and regions

## Test Scripts

The repository includes the following test scripts:
- `s3_transfer_manager_test.py`: Tests the S3 Transfer Manager
- `s3_crt_test.py`: Tests the S3 CRT Client
- `s3_optimized_transfer.py`: Tests the optimized S3 transfer configuration with and without acceleration

## Dependencies

- Python 3.x
- boto3
- boto3[crt] for CRT client tests
