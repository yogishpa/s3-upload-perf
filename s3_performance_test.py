#!/usr/bin/env python3
"""
S3 Performance Testing Script

This script tests AWS S3 upload and download performance with various methods
including standard uploads, multipart uploads, and transfer acceleration.
"""

import os
import time
import uuid
import boto3
import logging
import threading
import statistics
from io import BytesIO
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REGION = 'us-east-1'  # Change to your preferred region
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB chunks for multipart upload
TEST_ITERATIONS = 3
UNIQUE_ID = str(uuid.uuid4())[:8]
STANDARD_BUCKET = f"s3-performance-test-standard-{UNIQUE_ID}"
ACCELERATED_BUCKET = f"s3-performance-test-accelerated-{UNIQUE_ID}"
TEST_FILE = "test.zip"  # Using existing test.zip file
TEST_VIDEO = "test.zip"  # Using the same file for download tests

# Create S3 clients
s3_client = boto3.client('s3', region_name=REGION)
s3_resource = boto3.resource('s3', region_name=REGION)


class ProgressPercentage:
    """Class for tracking upload/download progress"""
    def __init__(self, size, operation_name):
        self._size = size
        self._seen_so_far = 0
        self._start_time = time.time()
        self._operation_name = operation_name
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            elapsed_time = time.time() - self._start_time
            speed = self._seen_so_far / (1024 * 1024 * elapsed_time) if elapsed_time > 0 else 0
            
            logger.info(
                f"{self._operation_name}: {self._seen_so_far}/{self._size} "
                f"({percentage:.2f}%) - {speed:.2f} MB/s"
            )


def create_buckets():
    """Create test buckets with appropriate configurations"""
    buckets = []
    
    # Create standard bucket
    try:
        logger.info(f"Creating standard bucket: {STANDARD_BUCKET}")
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=STANDARD_BUCKET)
        else:
            s3_client.create_bucket(
                Bucket=STANDARD_BUCKET,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        buckets.append(STANDARD_BUCKET)
    except ClientError as e:
        logger.error(f"Error creating standard bucket: {e}")
        raise
    
    # Create accelerated bucket
    try:
        logger.info(f"Creating accelerated bucket: {ACCELERATED_BUCKET}")
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=ACCELERATED_BUCKET)
        else:
            s3_client.create_bucket(
                Bucket=ACCELERATED_BUCKET,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        
        # Enable transfer acceleration
        s3_client.put_bucket_accelerate_configuration(
            Bucket=ACCELERATED_BUCKET,
            AccelerateConfiguration={'Status': 'Enabled'}
        )
        buckets.append(ACCELERATED_BUCKET)
    except ClientError as e:
        logger.error(f"Error creating accelerated bucket: {e}")
        raise
    
    # Configure CORS for both buckets
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': ['ETag']
        }]
    }
    
    for bucket in buckets:
        try:
            s3_client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration=cors_configuration
            )
        except ClientError as e:
            logger.error(f"Error setting CORS for bucket {bucket}: {e}")
    
    logger.info("Buckets created successfully")
    return buckets


def normal_upload(file_path, bucket, key):
    """Perform a normal upload using upload_file"""
    file_size = os.path.getsize(file_path)
    start_time = time.time()
    
    try:
        s3_client.upload_file(
            file_path, 
            bucket, 
            key,
            Callback=ProgressPercentage(file_size, "Normal upload")
        )
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"Normal upload completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during normal upload: {e}")
        raise


def multipart_upload(file_path, bucket, key):
    """Perform a multipart upload using TransferConfig"""
    file_size = os.path.getsize(file_path)
    start_time = time.time()
    
    # Configure multipart upload
    config = TransferConfig(
        multipart_threshold=CHUNK_SIZE,
        max_concurrency=10,
        multipart_chunksize=CHUNK_SIZE,
        use_threads=True
    )
    
    try:
        s3_client.upload_file(
            file_path, 
            bucket, 
            key,
            Config=config,
            Callback=ProgressPercentage(file_size, "Multipart upload")
        )
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"Multipart upload completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during multipart upload: {e}")
        raise


def accelerated_upload(file_path, bucket, key, use_multipart=False):
    """Perform an upload with transfer acceleration"""
    file_size = os.path.getsize(file_path)
    start_time = time.time()
    
    # Create accelerated client
    s3_accelerated = boto3.client(
        's3',
        region_name=REGION,
        config=boto3.session.Config(s3={'use_accelerate_endpoint': True})
    )
    
    try:
        if use_multipart:
            # Configure multipart upload
            config = TransferConfig(
                multipart_threshold=CHUNK_SIZE,
                max_concurrency=10,
                multipart_chunksize=CHUNK_SIZE,
                use_threads=True
            )
            
            s3_accelerated.upload_file(
                file_path, 
                bucket, 
                key,
                Config=config,
                Callback=ProgressPercentage(file_size, "Accelerated multipart upload")
            )
        else:
            s3_accelerated.upload_file(
                file_path, 
                bucket, 
                key,
                Callback=ProgressPercentage(file_size, "Accelerated normal upload")
            )
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        upload_type = "multipart" if use_multipart else "normal"
        logger.info(f"Accelerated {upload_type} upload completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput
        }
    except ClientError as e:
        logger.error(f"Error during accelerated upload: {e}")
        raise


def direct_download_to_memory(bucket, key):
    """Download file directly to memory using BytesIO"""
    try:
        # Get object size first
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response['ContentLength']
        
        start_time = time.time()
        
        # Download to memory
        buffer = BytesIO()
        s3_client.download_fileobj(
            bucket, 
            key, 
            buffer,
            Callback=ProgressPercentage(file_size, "Direct memory download")
        )
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"Direct memory download completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput,
            'data_size': file_size
        }
    except ClientError as e:
        logger.error(f"Error during direct memory download: {e}")
        raise


def streaming_download(bucket, key, buffer_size=8 * 1024 * 1024):  # 8MB buffer
    """Download file using streaming with a specified buffer size"""
    try:
        # Get object size first
        response = s3_client.head_object(Bucket=bucket, Key=key)
        file_size = response['ContentLength']
        
        start_time = time.time()
        
        # Stream the download
        response = s3_client.get_object(Bucket=bucket, Key=key)
        stream = response['Body']
        
        # Read in chunks to simulate streaming
        total_read = 0
        buffer = BytesIO()
        
        while True:
            chunk = stream.read(buffer_size)
            if not chunk:
                break
            buffer.write(chunk)
            total_read += len(chunk)
            
            # Log progress
            percentage = (total_read / file_size) * 100
            elapsed = time.time() - start_time
            speed = total_read / (1024 * 1024 * elapsed) if elapsed > 0 else 0
            logger.info(f"Streaming download: {total_read}/{file_size} ({percentage:.2f}%) - {speed:.2f} MB/s")
        
        end_time = time.time()
        duration = end_time - start_time
        throughput = file_size / (1024 * 1024 * duration)
        
        logger.info(f"Streaming download completed in {duration:.2f} seconds")
        logger.info(f"Throughput: {throughput:.2f} MB/s")
        
        return {
            'duration': duration,
            'throughput': throughput,
            'data_size': file_size
        }
    except ClientError as e:
        logger.error(f"Error during streaming download: {e}")
        raise


def clean_up(buckets, local_files):
    """Clean up all created resources"""
    logger.info("Starting cleanup...")
    
    # Delete local files
    for file_path in local_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted local file: {file_path}")
            except OSError as e:
                logger.error(f"Error deleting file {file_path}: {e}")
    
    # Delete buckets and their contents
    for bucket_name in buckets:
        try:
            bucket = s3_resource.Bucket(bucket_name)
            bucket.objects.all().delete()
            logger.info(f"Deleted all objects in bucket: {bucket_name}")
            
            bucket.delete()
            logger.info(f"Deleted bucket: {bucket_name}")
        except ClientError as e:
            logger.error(f"Error deleting bucket {bucket_name}: {e}")
    
    logger.info("Cleanup completed")


def generate_report(results):
    """Generate a summary report of all test results"""
    logger.info("\n\n=== S3 PERFORMANCE TEST SUMMARY ===\n")
    
    # Helper function to calculate averages
    def calculate_averages(test_results):
        durations = [result['duration'] for result in test_results]
        throughputs = [result['throughput'] for result in test_results]
        
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
    
    # Print upload test results
    logger.info("UPLOAD PERFORMANCE (3GB file):")
    logger.info(f"{'Test Type':<30} {'Avg Duration (s)':<20} {'Avg Throughput (MB/s)':<20} {'Best Throughput (MB/s)':<20}")
    logger.info("-" * 90)
    
    for test_name in ['standard_normal_upload', 'standard_multipart_upload', 
                      'accelerated_normal_upload', 'accelerated_multipart_upload']:
        avg = averages[test_name]
        logger.info(f"{test_name:<30} {avg['avg_duration']:<20.2f} {avg['avg_throughput']:<20.2f} {avg['max_throughput']:<20.2f}")
    
    # Print download test results
    logger.info("\nDOWNLOAD PERFORMANCE (test.zip):")
    logger.info(f"{'Test Type':<30} {'Avg Duration (s)':<20} {'Avg Throughput (MB/s)':<20} {'Best Throughput (MB/s)':<20}")
    logger.info("-" * 90)
    
    for test_name in ['direct_memory_download', 'streaming_download']:
        avg = averages[test_name]
        logger.info(f"{test_name:<30} {avg['avg_duration']:<20.2f} {avg['avg_throughput']:<20.2f} {avg['max_throughput']:<20.2f}")
    
    # Determine best methods
    best_upload = max(
        ['standard_normal_upload', 'standard_multipart_upload', 
         'accelerated_normal_upload', 'accelerated_multipart_upload'],
        key=lambda x: averages[x]['avg_throughput']
    )
    
    best_download = max(
        ['direct_memory_download', 'streaming_download'],
        key=lambda x: averages[x]['avg_throughput']
    )
    
    logger.info("\nBEST PERFORMING METHODS:")
    logger.info(f"Best Upload Method: {best_upload} with {averages[best_upload]['avg_throughput']:.2f} MB/s")
    logger.info(f"Best Download Method: {best_download} with {averages[best_download]['avg_throughput']:.2f} MB/s")
    
    # Calculate improvement percentages
    if 'standard_normal_upload' in averages and 'accelerated_multipart_upload' in averages:
        standard = averages['standard_normal_upload']['avg_throughput']
        accelerated_mp = averages['accelerated_multipart_upload']['avg_throughput']
        improvement = ((accelerated_mp - standard) / standard) * 100
        logger.info(f"\nImprovement from Standard Upload to Accelerated Multipart: {improvement:.2f}%")
    
    logger.info("\n=== END OF REPORT ===\n")


def run_tests():
    """Run all performance tests and report results"""
    buckets = []  # Initialize buckets list outside try block
    
    results = {
        'standard_normal_upload': [],
        'standard_multipart_upload': [],
        'accelerated_normal_upload': [],
        'accelerated_multipart_upload': [],
        'direct_memory_download': [],
        'streaming_download': []
    }
    
    try:
        # Create test buckets
        buckets = create_buckets()
        
        # Verify test file exists
        if not os.path.exists(TEST_FILE):
            logger.error(f"Test file {TEST_FILE} not found. Please ensure it exists in the current directory.")
            return
        
        file_size = os.path.getsize(TEST_FILE)
        logger.info(f"Using existing test file: {TEST_FILE} ({file_size / (1024**3):.2f} GB)")
        
        # Upload test file to standard bucket for download tests
        logger.info("Uploading test file for download tests")
        s3_client.upload_file(TEST_FILE, STANDARD_BUCKET, TEST_VIDEO)
        
        # Run upload tests multiple times
        for i in range(TEST_ITERATIONS):
            logger.info(f"\n--- Test Iteration {i+1}/{TEST_ITERATIONS} ---\n")
            
            # Standard bucket tests
            logger.info("\n=== Standard Bucket Tests ===\n")
            results['standard_normal_upload'].append(
                normal_upload(TEST_FILE, STANDARD_BUCKET, f"normal_upload_{i}.bin")
            )
            results['standard_multipart_upload'].append(
                multipart_upload(TEST_FILE, STANDARD_BUCKET, f"multipart_upload_{i}.bin")
            )
            
            # Accelerated bucket tests
            logger.info("\n=== Accelerated Bucket Tests ===\n")
            results['accelerated_normal_upload'].append(
                accelerated_upload(TEST_FILE, ACCELERATED_BUCKET, f"acc_normal_upload_{i}.bin", use_multipart=False)
            )
            results['accelerated_multipart_upload'].append(
                accelerated_upload(TEST_FILE, ACCELERATED_BUCKET, f"acc_multipart_upload_{i}.bin", use_multipart=True)
            )
            
            # Download tests
            logger.info("\n=== Download Tests ===\n")
            results['direct_memory_download'].append(
                direct_download_to_memory(STANDARD_BUCKET, TEST_VIDEO)
            )
            results['streaming_download'].append(
                streaming_download(STANDARD_BUCKET, TEST_VIDEO)
            )
        
        # Generate summary report
        generate_report(results)
        
    except Exception as e:
        logger.error(f"An error occurred during testing: {e}")
    finally:
        # Clean up resources
        clean_up(buckets, [])  # Don't delete the test.zip file since it was provided


if __name__ == "__main__":
    run_tests()
