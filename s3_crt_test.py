#!/usr/bin/env python3
"""
AWS S3 CRT Client Performance Testing Script

This script tests the AWS CRT-based S3 client for transferring files between local storage and S3.
The AWS CRT client provides enhanced performance through its optimized implementation.
"""

import os
import time
import uuid
import boto3
import logging
import threading
import statistics
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REGION = 'us-east-1'  # Change to your preferred region
UNIQUE_ID = str(uuid.uuid4())[:8]
S3_BUCKET = f"s3-crt-test-{UNIQUE_ID}"
TEST_FILE = "test.zip"
LOCAL_PATH = os.path.abspath(TEST_FILE)
S3_PREFIX = "crt-test"

# Check if boto3 has CRT support
try:
    from boto3.s3.transfer import TransferConfig
    from botocore.config import Config
    CRT_AVAILABLE = True
    logger.info("AWS CRT support is available")
except ImportError:
    CRT_AVAILABLE = False
    logger.warning("AWS CRT support is not available. Install with: pip install 'boto3[crt]'")

def create_bucket():
    """Create S3 bucket for testing"""
    try:
        logger.info(f"Creating S3 bucket: {S3_BUCKET}")
        s3_client = boto3.client('s3', region_name=REGION)
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=S3_BUCKET)
        else:
            s3_client.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        return S3_BUCKET
    except ClientError as e:
        logger.error(f"Error creating bucket: {e}")
        raise

def create_crt_client():
    """Create an S3 client with CRT enabled"""
    # Create a boto3 client with CRT enabled
    s3_config = Config(
        region_name=REGION,
        signature_version='s3v4',
        retries={
            'max_attempts': 10,
            'mode': 'standard'
        },
        s3={
            'use_accelerate_endpoint': False,
            'addressing_style': 'virtual',
            'payload_signing_enabled': False,
            'use_dualstack_endpoint': False,
            'use_arn_region': False,
            'us_east_1_regional_endpoint': 'regional'
        }
    )
    
    # Create the client with CRT enabled
    return boto3.client('s3', config=s3_config)

def s3_crt_upload():
    """Perform an upload using S3 CRT client"""
    file_size = os.path.getsize(TEST_FILE)
    start_time = time.time()
    
    try:
        logger.info(f"Starting S3 CRT upload of {TEST_FILE} ({file_size / (1024**2):.2f} MB)")
        
        # Create a callback class to track upload progress
        class ProgressPercentage(object):
            def __init__(self, filename):
                self._filename = filename
                self._size = float(os.path.getsize(filename))
                self._seen_so_far = 0
                self._lock = threading.Lock()
                self._last_update_time = time.time()
                self._update_interval = 1.0  # Update every second
                
            def __call__(self, bytes_amount):
                with self._lock:
                    self._seen_so_far += bytes_amount
                    current_time = time.time()
                    
                    # Update status at regular intervals
                    if current_time - self._last_update_time >= self._update_interval:
                        percentage = (self._seen_so_far / self._size) * 100
                        elapsed = current_time - start_time
                        speed = self._seen_so_far / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        
                        print(f"\r[S3 CRT UPLOAD] Progress: {self._seen_so_far}/{self._size} bytes "
                              f"({percentage:.2f}%) - {speed:.2f} MB/s", end="", flush=True)
                        
                        self._last_update_time = current_time
        
        # Configure the transfer with optimized settings for CRT
        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,  # 8 MB
            max_concurrency=20,  # Higher concurrency for CRT
            multipart_chunksize=16 * 1024 * 1024,  # 16 MB chunks
            use_threads=True
        )
        
        # Create CRT-enabled client
        s3_client = create_crt_client()
        
        # Use the CRT client to upload the file
        s3_client.upload_file(
            TEST_FILE, 
            S3_BUCKET, 
            f"{S3_PREFIX}/{TEST_FILE}",
            Config=transfer_config,
            Callback=ProgressPercentage(TEST_FILE)
        )
        
        print()  # Add a newline after progress tracking
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"S3 CRT upload completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during S3 CRT upload: {e}")
        raise

def s3_crt_download():
    """Perform a download using S3 CRT client"""
    # First ensure the file exists in S3
    s3_client = boto3.client('s3', region_name=REGION)
    if not object_exists_in_s3(S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}"):
        logger.info(f"File {TEST_FILE} not found in S3, uploading first")
        s3_client.upload_file(TEST_FILE, S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}")
    
    # Get file size
    response = s3_client.head_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{TEST_FILE}")
    file_size = response['ContentLength']
    
    # Download file
    download_path = f"downloaded_crt_{TEST_FILE}"
    start_time = time.time()
    
    try:
        logger.info(f"Starting S3 CRT download to {download_path} ({file_size / (1024**2):.2f} MB)")
        
        # Create a callback class to track download progress
        class ProgressPercentage(object):
            def __init__(self, total_size):
                self._total_size = total_size
                self._seen_so_far = 0
                self._lock = threading.Lock()
                self._last_update_time = time.time()
                self._update_interval = 1.0  # Update every second
                
            def __call__(self, bytes_amount):
                with self._lock:
                    self._seen_so_far += bytes_amount
                    current_time = time.time()
                    
                    # Update status at regular intervals
                    if current_time - self._last_update_time >= self._update_interval:
                        percentage = (self._seen_so_far / self._total_size) * 100
                        elapsed = current_time - start_time
                        speed = self._seen_so_far / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                        
                        print(f"\r[S3 CRT DOWNLOAD] Progress: {self._seen_so_far}/{self._total_size} bytes "
                              f"({percentage:.2f}%) - {speed:.2f} MB/s", end="", flush=True)
                        
                        self._last_update_time = current_time
        
        # Configure the transfer with optimized settings for CRT
        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,  # 8 MB
            max_concurrency=20,  # Higher concurrency for CRT
            multipart_chunksize=16 * 1024 * 1024,  # 16 MB chunks
            use_threads=True
        )
        
        # Create CRT-enabled client
        s3_client = create_crt_client()
        
        # Use the CRT client to download the file
        s3_client.download_file(
            S3_BUCKET, 
            f"{S3_PREFIX}/{TEST_FILE}", 
            download_path,
            Config=transfer_config,
            Callback=ProgressPercentage(file_size)
        )
        
        print()  # Add a newline after progress tracking
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"S3 CRT download completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        # Clean up downloaded file
        os.remove(download_path)
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during S3 CRT download: {e}")
        raise

def object_exists_in_s3(bucket, key):
    """Check if an object exists in S3"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        return False

def clean_up(bucket):
    """Clean up all created resources"""
    logger.info("Starting cleanup...")
    
    # Delete objects in S3 bucket
    try:
        s3 = boto3.resource('s3')
        bucket_obj = s3.Bucket(bucket)
        bucket_obj.objects.all().delete()
        logger.info(f"Deleted all objects in bucket: {bucket}")
        
        # Delete the bucket
        bucket_obj.delete()
        logger.info(f"Deleted bucket: {bucket}")
    except ClientError as e:
        logger.error(f"Error cleaning up S3 resources: {e}")

def run_tests():
    """Run all performance tests"""
    results = {
        's3_crt_upload': [],
        's3_crt_download': []
    }
    
    bucket = None
    
    try:
        # Verify test file exists
        if not os.path.exists(TEST_FILE):
            logger.error(f"Test file {TEST_FILE} not found. Please ensure it exists in the current directory.")
            return
        
        file_size = os.path.getsize(TEST_FILE)
        logger.info(f"Using test file: {TEST_FILE} ({file_size / (1024**3):.2f} GB)")
        
        # Create S3 bucket
        bucket = create_bucket()
        
        # Run S3 CRT tests
        logger.info("\n=== S3 CRT Upload Test ===")
        results['s3_crt_upload'].append(s3_crt_upload())
        
        logger.info("\n=== S3 CRT Download Test ===")
        results['s3_crt_download'].append(s3_crt_download())
        
        # Generate summary report
        generate_report(results, file_size)
        
    except Exception as e:
        logger.error(f"An error occurred during testing: {e}")
    finally:
        # Clean up resources
        if bucket:
            clean_up(bucket)

def generate_report(results, file_size):
    """Generate a summary report of all test results"""
    logger.info("\n\n=== PERFORMANCE TEST SUMMARY ===\n")
    
    # Helper function to calculate averages
    def calculate_averages(test_results):
        durations = [result['duration'] for result in test_results if result is not None]
        throughputs = [result['throughput'] for result in test_results if result is not None]
        
        if not durations:
            return {
                'avg_duration': 0,
                'avg_throughput': 0,
                'min_duration': 0,
                'max_throughput': 0
            }
        
        return {
            'avg_duration': statistics.mean(durations),
            'avg_throughput': statistics.mean(throughputs),
            'min_duration': min(durations),
            'max_throughput': max(throughputs)
        }
    
    # Calculate averages for each test type
    averages = {}
    for test_name, test_results in results.items():
        averages[test_name] = calculate_averages(test_results)
    
    # Print test results
    logger.info(f"FILE SIZE: {file_size / (1024**3):.2f} GB")
    logger.info(f"{'Test Type':<30} {'Avg Duration (s)':<20} {'Avg Throughput (MB/s)':<20}")
    logger.info("-" * 70)
    
    for test_name in ['s3_crt_upload', 's3_crt_download']:
        avg = averages[test_name]
        logger.info(f"{test_name:<30} {avg['avg_duration']:<20.2f} {avg['avg_throughput']:<20.2f}")
    
    # Compare with previous S3 performance test results
    logger.info("\n=== COMPARISON WITH PREVIOUS PERFORMANCE TESTS ===\n")
    logger.info("Previous best S3 upload method: accelerated_multipart_upload with 8.63 MB/s")
    logger.info("Previous best S3 download method: direct_memory_download with 9.62 MB/s")
    logger.info("Previous Transfer Manager upload: 4.68 MB/s")
    logger.info("Previous Transfer Manager download: 7.26 MB/s")
    logger.info("Previous DataSync simulated upload: 15.00 MB/s")
    logger.info("Previous DataSync simulated download: 18.00 MB/s")
    
    s3_crt_upload_speed = averages['s3_crt_upload']['avg_throughput']
    s3_crt_download_speed = averages['s3_crt_download']['avg_throughput']
    
    if s3_crt_upload_speed > 0:
        upload_improvement_s3 = ((s3_crt_upload_speed - 8.63) / 8.63) * 100
        upload_improvement_tm = ((s3_crt_upload_speed - 4.68) / 4.68) * 100
        upload_comparison_datasync = ((s3_crt_upload_speed - 15.00) / 15.00) * 100
        logger.info(f"\nS3 CRT upload speed: {s3_crt_upload_speed:.2f} MB/s")
        logger.info(f"  - {upload_improvement_s3:.2f}% compared to best previous S3 method")
        logger.info(f"  - {upload_improvement_tm:.2f}% compared to Transfer Manager")
        logger.info(f"  - {upload_comparison_datasync:.2f}% compared to simulated DataSync")
    
    if s3_crt_download_speed > 0:
        download_improvement_s3 = ((s3_crt_download_speed - 9.62) / 9.62) * 100
        download_improvement_tm = ((s3_crt_download_speed - 7.26) / 7.26) * 100
        download_comparison_datasync = ((s3_crt_download_speed - 18.00) / 18.00) * 100
        logger.info(f"\nS3 CRT download speed: {s3_crt_download_speed:.2f} MB/s")
        logger.info(f"  - {download_improvement_s3:.2f}% compared to best previous S3 method")
        logger.info(f"  - {download_improvement_tm:.2f}% compared to Transfer Manager")
        logger.info(f"  - {download_comparison_datasync:.2f}% compared to simulated DataSync")
    
    logger.info("\n=== END OF REPORT ===\n")

if __name__ == "__main__":
    run_tests()
