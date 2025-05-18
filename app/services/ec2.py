import boto3
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_instance_price(instance_type, credentials, region="ap-south-1"):
    try:
        pricing = boto3.client(
            'pricing',
            region_name='us-east-1',  # Pricing API only supports us-east-1
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"]
        )

        response = pricing.get_products(
            ServiceCode='AmazonEC2',
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': 'Asia Pacific (Mumbai)'},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
            ],
            MaxResults=1
        )

        price_list = response.get('PriceList', [])
        if price_list:
            price_item = json.loads(price_list[0])
            on_demand = list(price_item['terms']['OnDemand'].values())[0]
            price_dimensions = list(on_demand['priceDimensions'].values())[0]
            price_per_hour = float(price_dimensions['pricePerUnit']['USD'])
            return round(price_per_hour * 24 * 30, 2)  # Monthly estimate
    except Exception as e:
        print("Pricing error:", e)
    return None

def get_regions_with_running_instances(credentials):
    ec2_client = boto3.client(
        'ec2',
        region_name='us-east-1',  # region for describe_regions call
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"]
    )

    try:
        all_regions = [r["RegionName"] for r in ec2_client.describe_regions()["Regions"]]
    except Exception as e:
        print(f"[ERROR] Unable to fetch regions: {e}")
        return []

    active_regions = []
    for region in all_regions:
        regional_ec2 = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"]
        )
        try:
            response = regional_ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}],
                MaxResults=5  # just check if there are any running instances
            )
            if response.get('Reservations'):
                active_regions.append(region)
        except Exception as e:
            print(f"[WARN] Could not check instances in {region}: {e}")
    return active_regions

def get_idle_instances_in_region(credentials, region):
    ec2_client = boto3.client(
        'ec2',
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
        region_name=region
    )

    cloudwatch = boto3.client(
        'cloudwatch',
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
        region_name=region
    )

    try:
        response = ec2_client.describe_instances(Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ])
    except Exception as e:
        print(f"[WARN] Failed to describe instances in {region}: {e}")
        return []

    idle_instances = []
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    for reservation in response.get('Reservations', []):
        for instance in reservation.get('Instances', []):
            instance_id = instance['InstanceId']
            instance_type = instance.get('InstanceType', 'unknown')
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            name = tags.get('Name', 'N/A')

            try:
                metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Average']
                )

                datapoints = metrics.get('Datapoints', [])
                if datapoints:
                    avg_cpu = sum(dp['Average'] for dp in datapoints) / len(datapoints)
                    if avg_cpu < 5:
                        estimated_cost = get_instance_price(instance_type, credentials, region)
                        idle_instances.append({
                            'InstanceId': instance_id,
                            'Name': name,
                            'InstanceType': instance_type,
                            'AverageCPU (%)': round(avg_cpu, 2),
                            'EstimatedMonthlyCost ($)': round(estimated_cost, 2) if estimated_cost else "N/A",
                            'LaunchTime': str(instance.get('LaunchTime')),
                            'Region': region
                        })
            except Exception as e:
                print(f"[WARN] CPU metric error in {region} for {instance_id}: {e}")

    return idle_instances

def get_idle_ec2_instances(credentials):
    active_regions = get_regions_with_running_instances(credentials)
    if not active_regions:
        print("[INFO] No active EC2 regions with running instances found.")
        return []

    print(f"[INFO] Scanning active regions: {active_regions}")

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_idle_instances_in_region, credentials, region): region for region in active_regions}
        for future in as_completed(futures):
            region = futures[future]
            try:
                result = future.result(timeout=60)
                results.extend(result)
            except Exception as e:
                print(f"[WARN] Skipping region {region} due to error: {e}")

    return results

