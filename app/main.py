from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import boto3
from botocore.exceptions import ClientError
import os

from app.auth import register_user, login_user, verify_password
# from app.routes import resources  # Uncomment if you have this router

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Uncomment if you have the resources router
# app.include_router(resources.router, prefix="/resources", tags=["resources"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session Middleware for session handling (store AWS creds in cookie session)
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "default_insecure_key_for_dev")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

def get_credentials_from_session(request: Request):
    return request.session.get("aws_credentials", None)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = login_user(email)
    if not user or not verify_password(password, user["password"]):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    result = register_user(name, email, password)
    if isinstance(result, dict) and result.get("error"):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": result["error"]
        })
    return RedirectResponse(url="/login", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/connect", response_class=HTMLResponse)
async def connect_aws_form(request: Request):
    return templates.TemplateResponse("connect.html", {"request": request})

@app.post("/connect")
async def connect_aws(
    request: Request,
    access_key: str = Form(...),
    secret_key: str = Form(...)
):
    try:
        sts_client = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        sts_client.get_caller_identity()
    except ClientError:
        return templates.TemplateResponse("connect.html", {
            "request": request,
            "error": "Invalid AWS credentials, please try again."
        })

    request.session["aws_credentials"] = {
        "access_key": access_key,
        "secret_key": secret_key
    }

    return RedirectResponse(url="/idle-resources", status_code=303)

@app.get("/idle-resources", response_class=HTMLResponse)
async def idle_resources_dashboard(request: Request):
    if "aws_credentials" not in request.session:
        return RedirectResponse(url="/connect", status_code=303)
    return templates.TemplateResponse("idle_resources.html", {"request": request})

@app.post("/idle-resources", response_class=HTMLResponse)
async def scan_idle_resources(request: Request):
    credentials = get_credentials_from_session(request)
    if not credentials:
        return RedirectResponse(url="/connect", status_code=303)
    try:
        # Your actual scan logic using boto3 and credentials here
        idle_ebs = []  # Placeholder: Replace with boto3 logic
        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "idle_ebs": idle_ebs
        })
    except Exception as e:
        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "error": str(e)
        })
