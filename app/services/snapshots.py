import boto3
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

# Get all available regions (opted-in or not required)
def get_all_regions(credentials):
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name="us-east-1"
        )
        regions = ec2.describe_regions(AllRegions=True)["Regions"]
        return [r["RegionName"] for r in regions if r["OptInStatus"] in ("opt-in-not-required", "opted-in")]
    except Exception as e:
        print(f"[ERROR] Failed to retrieve regions: {e}")
        return []

# Get idle snapshots for a specific region
def get_idle_snapshots_in_region(region, credentials):
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=credentials["access_key"],
        aws_secret_access_key=credentials["secret_key"],
        region_name=region
    )

    idle_snapshots = []
    threshold_date = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        response = ec2.describe_snapshots(OwnerIds=["self"])
        snapshots = response.get("Snapshots", [])

        for snap in snapshots:
            if snap["StartTime"] < threshold_date:
                size_gb = snap.get("VolumeSize", 0)
                estimated_cost = round(size_gb * 0.05, 2)
                usage_cost = 0.0  # Assuming no usage
                idle_snapshots.append({
                    "SnapshotId": snap["SnapshotId"],
                    "StartTime": snap["StartTime"].strftime("%Y-%m-%d"),
                    "VolumeSize (GB)": size_gb,
                    "EstimatedMonthlyCost ($)": estimated_cost,
                    "UsageCost ($)": usage_cost,
                    "SavedCost ($)": estimated_cost - usage_cost,
                    "Region": region
                })
    except Exception as e:
        print(f"[WARN] Skipping region {region} due to error: {e}")

    return idle_snapshots

# Scan all regions in parallel for idle snapshots
def get_idle_snapshots(credentials):
    all_idle_snapshots = []
    regions = get_all_regions(credentials)

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_idle_snapshots_in_region, region, credentials) for region in regions]
        for future in futures:
            try:
                all_idle_snapshots.extend(future.result())
            except Exception as e:
                print(f"[ERROR] Error in snapshot future: {e}")

    return all_idle_snapshots

# Delete snapshot in a given region
def delete_snapshot(snapshot_id, credentials, region):
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=credentials["access_key"],
            aws_secret_access_key=credentials["secret_key"],
            region_name=region
        )
        ec2.delete_snapshot(SnapshotId=snapshot_id)
    except Exception as e:
        raise Exception(f"[ERROR] Failed to delete snapshot {snapshot_id} in {region}: {str(e)}")

