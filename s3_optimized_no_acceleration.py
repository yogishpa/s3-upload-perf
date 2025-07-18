#!/usr/bin/env python3
"""
Optimized S3 Performance Testing Script (No Acceleration)

This script tests AWS S3 upload and download performance with optimized settings
but without using Transfer Acceleration to avoid additional costs.
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
from botocore.config import Config
from boto3.s3.transfer import TransferConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REGION = 'us-east-1'  # Change to your preferred region
UNIQUE_ID = str(uuid.uuid4())[:8]
S3_BUCKET = f"s3-optimized-test-{UNIQUE_ID}"
TEST_FILE = "test.zip"
LOCAL_PATH = os.path.abspath(TEST_FILE)
S3_PREFIX = "optimized-test"
TEST_ITERATIONS = 1  # Number of test iterations

def create_bucket():
    """Create S3 bucket for testing"""
    try:
        logger.info(f"Creating S3 bucket: {S3_BUCKET}")
        s3_client = boto3.client('s3', region_name=REGION)
        
        # Create the bucket
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

def create_optimized_client():
    """Create an optimized S3 client with best performance settings"""
    # Create a boto3 client with optimized settings
    s3_config = Config(
        region_name=REGION,
        signature_version='s3v4',
        retries={
            'max_attempts': 10,
            'mode': 'adaptive'  # Use adaptive retry mode for better resilience
        },
        s3={
            'addressing_style': 'virtual',
            'payload_signing_enabled': False,  # Improves performance
            'use_dualstack_endpoint': False,
            'us_east_1_regional_endpoint': 'regional'
        },
        # Increase max pool connections for better concurrency
        max_pool_connections=50
    )
    
    # Create the client
    return boto3.client('s3', config=s3_config)

def get_optimized_transfer_config(for_upload=True):
    """Get optimized transfer configuration based on operation type"""
    if for_upload:
        # For uploads, use slightly lower concurrency but larger chunk size
        return TransferConfig(
            multipart_threshold=25 * 1024 * 1024,  # 25 MB
            max_concurrency=15,                    # 15 concurrent threads
            multipart_chunksize=25 * 1024 * 1024,  # 25 MB chunks
            use_threads=True,
            max_bandwidth=None                     # No bandwidth limit
        )
    else:
        # For downloads, use higher concurrency
        return TransferConfig(
            multipart_threshold=25 * 1024 * 1024,  # 25 MB
            max_concurrency=20,                    # 20 concurrent threads
            multipart_chunksize=25 * 1024 * 1024,  # 25 MB chunks
            use_threads=True,
            max_bandwidth=None                     # No bandwidth limit
        )

def optimized_upload():
    """Perform an upload using optimized settings"""
    file_size = os.path.getsize(TEST_FILE)
    start_time = time.time()
    
    try:
        logger.info(f"Starting optimized S3 upload of {TEST_FILE} ({file_size / (1024**2):.2f} MB)")
        
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
                        
                        print(f"\r[OPTIMIZED UPLOAD] Progress: {self._seen_so_far}/{self._size} bytes "
                              f"({percentage:.2f}%) - {speed:.2f} MB/s", end="", flush=True)
                        
                        self._last_update_time = current_time
        
        # Get optimized transfer config
        transfer_config = get_optimized_transfer_config(for_upload=True)
        
        # Create optimized client
        s3_client = create_optimized_client()
        
        # Use the client to upload the file
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
        
        logger.info(f"Optimized S3 upload completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during optimized S3 upload: {e}")
        raise

def optimized_download():
    """Perform a download using optimized settings"""
    # First ensure the file exists in S3
    standard_s3 = boto3.client('s3', region_name=REGION)
    if not object_exists_in_s3(S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}"):
        logger.info(f"File {TEST_FILE} not found in S3, uploading first")
        standard_s3.upload_file(TEST_FILE, S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}")
    
    # Get file size
    response = standard_s3.head_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{TEST_FILE}")
    file_size = response['ContentLength']
    
    # Download file
    download_path = f"downloaded_optimized_{TEST_FILE}"
    start_time = time.time()
    
    try:
        logger.info(f"Starting optimized S3 download to {download_path} ({file_size / (1024**2):.2f} MB)")
        
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
                        
                        print(f"\r[OPTIMIZED DOWNLOAD] Progress: {self._seen_so_far}/{self._total_size} bytes "
                              f"({percentage:.2f}%) - {speed:.2f} MB/s", end="", flush=True)
                        
                        self._last_update_time = current_time
        
        # Get optimized transfer config
        transfer_config = get_optimized_transfer_config(for_upload=False)
        
        # Create optimized client
        s3_client = create_optimized_client()
        
        # Use the client to download the file
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
        
        logger.info(f"Optimized S3 download completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        # Clean up downloaded file
        os.remove(download_path)
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during optimized S3 download: {e}")
        raise

def optimized_range_download():
    """Perform a download using optimized settings with range requests"""
    # First ensure the file exists in S3
    standard_s3 = boto3.client('s3', region_name=REGION)
    if not object_exists_in_s3(S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}"):
        logger.info(f"File {TEST_FILE} not found in S3, uploading first")
        standard_s3.upload_file(TEST_FILE, S3_BUCKET, f"{S3_PREFIX}/{TEST_FILE}")
    
    # Get file size
    response = standard_s3.head_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/{TEST_FILE}")
    file_size = response['ContentLength']
    
    # Download file using range requests
    download_path = f"downloaded_range_{TEST_FILE}"
    start_time = time.time()
    
    try:
        logger.info(f"Starting optimized range S3 download to {download_path} ({file_size / (1024**2):.2f} MB)")
        
        # Create optimized client
        s3_client = create_optimized_client()
        
        # Calculate chunk size and number of chunks
        chunk_size = 25 * 1024 * 1024  # 25 MB chunks
        num_chunks = (file_size + chunk_size - 1) // chunk_size  # Ceiling division
        
        # Create threads for parallel downloads
        threads = []
        downloaded_bytes = [0]  # Use list for mutable reference in threads
        lock = threading.Lock()
        
        def download_chunk(chunk_index):
            start_byte = chunk_index * chunk_size
            end_byte = min(start_byte + chunk_size - 1, file_size - 1)
            
            # Download the chunk
            response = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=f"{S3_PREFIX}/{TEST_FILE}",
                Range=f"bytes={start_byte}-{end_byte}"
            )
            
            chunk_data = response['Body'].read()
            
            # Write to file at correct position
            with open(download_path, 'r+b' if os.path.exists(download_path) else 'wb') as f:
                f.seek(start_byte)
                f.write(chunk_data)
            
            # Update progress
            with lock:
                downloaded_bytes[0] += len(chunk_data)
                percentage = (downloaded_bytes[0] / file_size) * 100
                elapsed = time.time() - start_time
                speed = downloaded_bytes[0] / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                print(f"\r[OPTIMIZED RANGE DOWNLOAD] Progress: {downloaded_bytes[0]}/{file_size} bytes "
                      f"({percentage:.2f}%) - {speed:.2f} MB/s", end="", flush=True)
        
        # Create file with correct size
        with open(download_path, 'wb') as f:
            f.seek(file_size - 1)
            f.write(b'\0')
        
        # Start download threads
        max_threads = 20  # Maximum concurrent threads
        for i in range(num_chunks):
            thread = threading.Thread(target=download_chunk, args=(i,))
            threads.append(thread)
            thread.start()
            
            # Limit concurrent threads
            if len(threads) >= max_threads:
                threads[0].join()
                threads.pop(0)
        
        # Wait for remaining threads
        for thread in threads:
            thread.join()
        
        print()  # Add a newline after progress tracking
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"Optimized range S3 download completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        # Clean up downloaded file
        os.remove(download_path)
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except (ClientError, Exception) as e:
        logger.error(f"Error during optimized range S3 download: {e}")
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
        'optimized_upload': [],
        'optimized_download': [],
        'optimized_range_download': []
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
        
        # Run tests multiple times for more accurate results
        for i in range(TEST_ITERATIONS):
            logger.info(f"\n--- Test Iteration {i+1}/{TEST_ITERATIONS} ---\n")
            
            # Run optimized upload test
            logger.info("\n=== Optimized S3 Upload Test ===")
            results['optimized_upload'].append(optimized_upload())
            
            # Run optimized download test
            logger.info("\n=== Optimized S3 Download Test ===")
            results['optimized_download'].append(optimized_download())
            
            # Run optimized range download test
            logger.info("\n=== Optimized S3 Range Download Test ===")
            results['optimized_range_download'].append(optimized_range_download())
        
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
    logger.info("\n\n=== OPTIMIZED PERFORMANCE TEST SUMMARY ===\n")
    
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
    logger.info(f"{'Test Type':<30} {'Avg Duration (s)':<20} {'Avg Throughput (MB/s)':<20} {'Best Throughput (MB/s)':<20}")
    logger.info("-" * 90)
    
    for test_name in ['optimized_upload', 'optimized_download', 'optimized_range_download']:
        avg = averages[test_name]
        logger.info(f"{test_name:<30} {avg['avg_duration']:<20.2f} {avg['avg_throughput']:<20.2f} {avg['max_throughput']:<20.2f}")
    
    # Compare with previous S3 performance test results
    logger.info("\n=== COMPARISON WITH PREVIOUS PERFORMANCE TESTS ===\n")
    logger.info("Previous standard S3 direct upload: 7.00 MB/s")
    logger.info("Previous standard S3 direct download: 7.58 MB/s")
    logger.info("Previous S3 Transfer Manager upload: 4.68 MB/s")
    logger.info("Previous S3 Transfer Manager download: 7.26 MB/s")
    logger.info("Previous S3 CRT Client upload: 6.38 MB/s")
    logger.info("Previous S3 CRT Client download: 30.90 MB/s")
    
    # Calculate improvement percentages
    optimized_upload_speed = averages['optimized_upload']['avg_throughput']
    optimized_download_speed = averages['optimized_download']['avg_throughput']
    optimized_range_download_speed = averages['optimized_range_download']['avg_throughput']
    
    if optimized_upload_speed > 0:
        vs_direct = ((optimized_upload_speed - 7.00) / 7.00) * 100
        vs_crt = ((optimized_upload_speed - 6.38) / 6.38) * 100
        logger.info(f"\nOptimized upload speed: {optimized_upload_speed:.2f} MB/s")
        logger.info(f"  - {vs_direct:.2f}% compared to standard S3 direct")
        logger.info(f"  - {vs_crt:.2f}% compared to S3 CRT Client")
    
    if optimized_download_speed > 0:
        vs_direct = ((optimized_download_speed - 7.58) / 7.58) * 100
        vs_crt = ((optimized_download_speed - 30.90) / 30.90) * 100
        logger.info(f"\nOptimized download speed: {optimized_download_speed:.2f} MB/s")
        logger.info(f"  - {vs_direct:.2f}% compared to standard S3 direct")
        logger.info(f"  - {vs_crt:.2f}% compared to S3 CRT Client")
    
    if optimized_range_download_speed > 0:
        vs_direct = ((optimized_range_download_speed - 7.58) / 7.58) * 100
        vs_crt = ((optimized_range_download_speed - 30.90) / 30.90) * 100
        vs_optimized = ((optimized_range_download_speed - optimized_download_speed) / optimized_download_speed) * 100
        logger.info(f"\nOptimized range download speed: {optimized_range_download_speed:.2f} MB/s")
        logger.info(f"  - {vs_direct:.2f}% compared to standard S3 direct")
        logger.info(f"  - {vs_crt:.2f}% compared to S3 CRT Client")
        logger.info(f"  - {vs_optimized:.2f}% compared to optimized download")
    
    logger.info("\n=== COST ANALYSIS ===\n")
    logger.info("This implementation avoids S3 Transfer Acceleration costs ($0.04/GB) while still achieving excellent performance.")
    logger.info(f"Cost savings for this {file_size / (1024**3):.2f} GB file: ${(file_size / (1024**3)) * 0.04:.2f} per transfer")
    
    logger.info("\n=== END OF REPORT ===\n")

if __name__ == "__main__":
    run_tests()
