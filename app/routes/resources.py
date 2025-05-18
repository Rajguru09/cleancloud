from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import os

from app.services.ec2 import get_idle_ec2_instances
from app.services.s3 import get_idle_s3_buckets
from app.services.ebs import get_idle_ebs_volumes
from app.services.eip import get_idle_eips
from app.services.snapshots import get_idle_snapshots

router = APIRouter(prefix="/resources", tags=["AWS Resources"])

# Dummy credentials function — replace with session-based logic
def get_credentials_from_session():
    return {
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY")
    }

class ScanRequest(BaseModel):
    resource_types: List[str]
    regions: List[str]  # You can use this to filter regions if supported later

@router.post("/scan")
async def scan_all_idle_resources(
    request: ScanRequest,
    credentials: dict = Depends(get_credentials_from_session)
):
    try:
        results = {}

        if "EC2" in request.resource_types:
            results["idle_ec2"] = get_idle_ec2_instances(credentials)

        if "S3" in request.resource_types:
            results["idle_s3"] = get_idle_s3_buckets(credentials)

        if "EBS" in request.resource_types:
            results["idle_ebs"] = get_idle_ebs_volumes(credentials)

        if "EIP" in request.resource_types:
            results["idle_eip"] = get_idle_eips(credentials)

        if "Snapshots" in request.resource_types:
            results["idle_snapshots"] = get_idle_snapshots(credentials)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

