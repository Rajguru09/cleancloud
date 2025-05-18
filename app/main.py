from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.auth import register_user, login_user, verify_password
from app.routes import resources  # Assuming you have this, otherwise remove this line and the router include

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Uncomment this if you have routes/resources router, else comment out
# app.include_router(resources.router, prefix="/resources", tags=["resources"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_credentials_from_session(request: Request):
    return {
        "access_key": "YOUR_ACCESS_KEY",
        "secret_key": "YOUR_SECRET_KEY"
    }

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

@app.get("/idle-resources", response_class=HTMLResponse)
async def idle_resources_dashboard(request: Request):
    return templates.TemplateResponse("idle_resources.html", {"request": request})

@app.post("/idle-resources", response_class=HTMLResponse)
async def scan_idle_resources(request: Request):
    credentials = get_credentials_from_session(request)
    try:
        idle_ebs = []  # Replace with your actual scan function
        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "idle_ebs": idle_ebs
        })
    except Exception as e:
        return templates.TemplateResponse("idle_resources.html", {
            "request": request,
            "error": str(e)
        })
