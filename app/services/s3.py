import boto3
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_all_regions(credentials):
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name="us-east-1"
        )
        return [region['RegionName'] for region in ec2.describe_regions()['Regions']]
    except Exception as e:
        print("[ERROR] Failed to get AWS regions:", e)
        return []

def get_metrics_for_bucket(bucket_name, credentials, region, start_time, end_time):
    try:
        cloudwatch = boto3.client(
            'cloudwatch',
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=region
        )

        metrics = cloudwatch.get_metric_statistics(
            Namespace='AWS/S3',
            MetricName='NumberOfObjects',
            Dimensions=[
                {'Name': 'BucketName', 'Value': bucket_name},
                {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,
            Statistics=['Sum']
        )
        return metrics.get('Datapoints', [])
    except Exception as e:
        # Log the error for debugging
        print(f"[WARN] Failed to get metrics for bucket {bucket_name} in region {region}: {e}")
        return []

def get_idle_s3_buckets(credentials):
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"]
        )

        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
        idle_buckets = []

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        regions = get_all_regions(credentials)

        for bucket in buckets:
            bucket_name = bucket['Name']
            is_idle = True

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(get_metrics_for_bucket, bucket_name, credentials, region, start_time, end_time): region
                    for region in regions
                }

                for future in as_completed(futures):
                    datapoints = future.result()
                    if datapoints:
                        # If there is any datapoint in any region, bucket is not idle
                        is_idle = False
                        break

            if is_idle:
                # Placeholder cost — can replace with real cost estimation logic
                estimated_cost = 0.02
                usage_cost = 0.0
                saved_cost = round(estimated_cost - usage_cost, 2)

                idle_buckets.append({
                    "Name": bucket_name,
                    "EstimatedMonthlyCost ($)": estimated_cost,
                    "UsageCost ($)": usage_cost,
                    "SavedCost ($)": saved_cost
                })

        return idle_buckets

    except Exception as e:
        print("[ERROR] Failed to get idle S3 buckets:", e)
        return []

def delete_s3_bucket(bucket_name, credentials):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"]
    )

    try:
        paginator = s3_client.get_paginator('list_object_versions')
        for page in paginator.paginate(Bucket=bucket_name):
            versions = page.get('Versions', []) + page.get('DeleteMarkers', [])
            for obj in versions:
                s3_client.delete_object(
                    Bucket=bucket_name,
                    Key=obj['Key'],
                    VersionId=obj['VersionId']
                )
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"[INFO] Bucket {bucket_name} deleted successfully.")
    except Exception as e:
        raise Exception(f"[ERROR] Failed to delete S3 bucket {bucket_name}: {str(e)}")

