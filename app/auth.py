import boto3
from passlib.context import CryptContext
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('users')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def register_user(name: str, email: str, password: str):
    hashed_pw = pwd_context.hash(password)
    try:
        table.put_item(
            Item={
                'email': email,
                'name': name,
                'password': hashed_pw
            },
            ConditionExpression='attribute_not_exists(email)'  # Avoid overwrite
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {"error": "User already exists"}
        raise

def login_user(email: str):
    try:
        response = table.get_item(Key={'email': email})
        return response.get('Item')
    except Exception as e:
        print("Error fetching user:", e)
        return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

