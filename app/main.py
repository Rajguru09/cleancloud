from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.auth import register_user, login_user, verify_password
from app.routes import resources  # Your API router for resource scanning

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

# Mount static files directory (for CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(resources.router)

# Include your resource scanning API router with prefix and tags
app.include_router(resources.router, prefix="/resources", tags=["resources"])

# CORS middleware setup (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL here for better security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Placeholder for retrieving AWS credentials from user session (replace with real implementation)
def get_credentials_from_session(request: Request):
    # Example static creds, replace with session retrieval or secure store
    return {
        "access_key": "YOUR_ACCESS_KEY",
        "secret_key": "YOUR_SECRET_KEY"
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(
    name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    confirm_password: str = Form(...)
):
    if password != confirm_password:
        return {"error": "Passwords do not match"}
    result = register_user(name, email, password)
    return RedirectResponse(url="/", status_code=303)

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    user = login_user(email)
    if not user or not verify_password(password, user["password"]):
        return {"error": "Invalid credentials"}
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # You can pass user info, AWS credentials, or other context here
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/idle-resources", response_class=HTMLResponse)
async def idle_resources_dashboard(request: Request):
    return templates.TemplateResponse("idle_resources.html", {"request": request})

@app.post("/idle-resources", response_class=HTMLResponse)
async def scan_idle_resources(request: Request):
    credentials = get_credentials_from_session(request)

    try:
        # Call your service function
        idle_ebs = get_idle_ebs_volumes(credentials)

        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "idle_ebs": idle_ebs  # Send data to the template
        })
    except Exception as e:
        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "error": str(e)
        })


