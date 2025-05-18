import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_all_regions(credentials):
    """
    Retrieve all AWS regions available.
    """
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name="us-east-1"
        )
        regions = ec2.describe_regions()["Regions"]
        return [region["RegionName"] for region in regions]
    except Exception as e:
        print("[ERROR] Failed to retrieve regions:", e)
        return []

def get_idle_ebs_volumes(credentials):
    """
    Fetch all available (idle) EBS volumes across regions.
    Assumes a placeholder monthly cost per GB (can be updated per pricing).
    """
    price_per_gb = 0.08  # Estimated $/GB per month for gp2/gp3 (check current AWS pricing)
    regions = get_all_regions(credentials)
    idle_volumes = []

    def scan_region_for_volumes(region):
        try:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=credentials["access_key"],
                aws_secret_access_key=credentials["secret_key"],
                region_name=region
            )
            volumes = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])["Volumes"]

            region_volumes = []
            for vol in volumes:
                size = vol.get("Size", 0)
                cost = round(size * price_per_gb, 2)
                region_volumes.append({
                    "VolumeId": vol["VolumeId"],
                    "Size (GB)": size,
                    "VolumeType": vol.get("VolumeType", "unknown"),
                    "EstimatedMonthlyCost ($)": cost,
                    "UsageCost ($)": 0.00,
                    "SavedCost ($)": cost,
                    "Region": region
                })
            print(f"[INFO] Found {len(region_volumes)} idle volumes in {region}")
            return region_volumes
        except Exception as e:
            print(f"[WARN] Failed to scan EBS volumes in region {region}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scan_region_for_volumes, region): region for region in regions}
        for future in as_completed(futures, timeout=120):
            region = futures[future]
            try:
                volumes = future.result()
                idle_volumes.extend(volumes)
            except Exception as e:
                print(f"[WARN] Skipping region {region} due to error: {e}")

    print(f"[INFO] Total idle EBS volumes found: {len(idle_volumes)}")
    return idle_volumes

def delete_ebs_volume(volume_id, credentials, region):
    """
    Deletes the specified EBS volume.
    """
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=region
        )
        ec2.delete_volume(VolumeId=volume_id)
        print(f"[INFO] Deleted EBS volume {volume_id} in {region}")
    except Exception as e:
        raise Exception(f"[ERROR] Failed to delete EBS volume {volume_id} in {region}: {str(e)}")

