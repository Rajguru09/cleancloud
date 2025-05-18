import boto3
from concurrent.futures import ThreadPoolExecutor

# Get all regions where the account can operate
def get_all_regions(credentials):
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name="us-east-1"
        )
        return [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    except Exception as e:
        print(f"[ERROR] Failed to fetch AWS regions: {e}")
        return []

# Identify idle EIPs in a single region
def get_eips_in_region(credentials, region):
    try:
        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=region
        )

        idle = []
        response = ec2.describe_addresses()

        for address in response.get('Addresses', []):
            if not address.get('AssociationId'):
                estimated_cost = 3.65  # Monthly idle EIP cost (as per AWS)
                usage_cost = 0.00
                saved_cost = round(estimated_cost - usage_cost, 2)

                idle.append({
                    "ElasticIP": address.get("PublicIp", "Unknown"),
                    "Status": "Idle",
                    "AllocationId": address.get("AllocationId"),
                    "Region": region,
                    "EstimatedMonthlyCost ($)": estimated_cost,
                    "UsageCost ($)": usage_cost,
                    "SavedCost ($)": saved_cost
                })

        return idle
    except Exception as e:
        print(f"[WARN] Skipping region {region} due to: {e}")
        return []

# Scan all AWS regions for idle EIPs
def get_idle_eips(credentials):
    idle_eips = []
    regions = get_all_regions(credentials)

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_eips_in_region, credentials, region) for region in regions]
        for future in futures:
            try:
                idle_eips.extend(future.result())
            except Exception as e:
                print(f"[ERROR] Thread failed: {e}")

    return idle_eips

# Release an Elastic IP using its Allocation ID
def delete_eip(eip_allocation_id, credentials, region):
    try:
        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=region
        )
        ec2.release_address(AllocationId=eip_allocation_id)
    except Exception as e:
        raise Exception(f"[ERROR] Failed to release EIP {eip_allocation_id} in {region}: {str(e)}")

