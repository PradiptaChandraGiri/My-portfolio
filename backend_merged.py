import os
import json
import uuid
import shutil
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# =====================================================================
# 1. Configuration and Base Setup
# =====================================================================

APP_TITLE = "Pradipta Portfolio Backend"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Essential directories
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_DIR = os.path.join(BASE_DIR, "db")

# JSON database files
PROFILE_JSON = os.path.join(DB_DIR, "profile.json")
PROJECTS_JSON = os.path.join(DB_DIR, "projects.json")
CONFIG_JSON = os.path.join(DB_DIR, "config.json")

# Upload sub-folders
PROFILE_DIR = os.path.join(UPLOADS_DIR, "profile")
PROJECTS_DIR = os.path.join(UPLOADS_DIR, "projects")

# Ensure directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


# =====================================================================
# 2. Utility Functions
# =====================================================================

def load_json(path):
    """Loads JSON safely. If missing, create default structure."""
    if not os.path.exists(path):
        if path.endswith("profile.json"):
            return {
                "name": "",
                "email": "",
                "linkedin": "",
                "github": "",
                "tagline": "",
                "about": "",
                "photo_path": "",
                "resume_path": ""
            }
        if path.endswith("projects.json"):
            return []
        if path.endswith("config.json"):
            return {
                "skills": {},
                "certifications": [],
                "offerings": [],
                "contact_info": {}
            }
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        return {}


def save_json(path, data):
    """Saves JSON into file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_upload_file(file, folder):
    """Stores uploaded file inside folder and returns filename + path."""
    os.makedirs(folder, exist_ok=True)
    ext = file.filename.split(".")[-1] if "." in file.filename else ""
    filename = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
    full_path = os.path.join(folder, filename)

    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename, full_path


# =====================================================================
# 3. Routers
# =====================================================================

profile_router = APIRouter()
projects_router = APIRouter()
config_router = APIRouter()

# ------------ PROFILE ROUTES ----------------
@profile_router.get("/")
def get_profile():
    return load_json(PROFILE_JSON)

@profile_router.post("/update")
def update_profile(data: dict):
    current = load_json(PROFILE_JSON)
    for k, v in data.items():
        if v is not None:
            current[k] = v
    save_json(PROFILE_JSON, current)
    return {"ok": True, "profile": current}

@profile_router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    filename, _ = save_upload_file(file, PROFILE_DIR)
    profile = load_json(PROFILE_JSON)
    profile["photo_path"] = f"/uploads/profile/{filename}"
    save_json(PROFILE_JSON, profile)
    return {"ok": True, "path": profile["photo_path"]}

@profile_router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF")
    filename, _ = save_upload_file(file, PROFILE_DIR)
    profile = load_json(PROFILE_JSON)
    profile["resume_path"] = f"/uploads/profile/{filename}"
    save_json(PROFILE_JSON, profile)
    return {"ok": True, "path": profile["resume_path"]}


# ------------ PROJECT ROUTES ----------------
@projects_router.get("/")
def get_projects():
    return load_json(PROJECTS_JSON)

@projects_router.post("/add")
def add_project(data: dict):
    projects = load_json(PROJECTS_JSON)
    new_project = {
        "id": str(uuid.uuid4()),
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "techStack": data.get("techStack", []),
        "highlights": data.get("highlights", []),
        "githubUrl": data.get("githubUrl", ""),
        "demoUrl": data.get("demoUrl", ""),
        "imagePath": data.get("imagePath", None),
    }
    projects.append(new_project)
    save_json(PROJECTS_JSON, projects)
    return {"ok": True, "project": new_project}

@projects_router.post("/delete")
def delete_project(project_id: str):
    projects = load_json(PROJECTS_JSON)
    new_projects = [p for p in projects if p["id"] != project_id]
    if len(new_projects) == len(projects):
        raise HTTPException(status_code=404, detail="Project not found")
    save_json(PROJECTS_JSON, new_projects)
    return {"ok": True}

@projects_router.post("/upload-image/{project_id}")
async def upload_project_image(project_id: str, file: UploadFile = File(...)):
    filename, _ = save_upload_file(file, PROJECTS_DIR)
    projects = load_json(PROJECTS_JSON)
    for p in projects:
        if p["id"] == project_id:
            p["imagePath"] = f"/uploads/projects/{filename}"
            save_json(PROJECTS_JSON, projects)
            return {"ok": True, "path": p["imagePath"]}
    raise HTTPException(status_code=404, detail="Project not found")


# ------------ CONFIG ROUTES ----------------
@config_router.get("/")
def get_config():
    return load_json(CONFIG_JSON)

@config_router.post("/update")
def update_config(data: dict):
    save_json(CONFIG_JSON, data)
    return {"ok": True}


# =====================================================================
# 4. FASTAPI INITIALIZATION
# =====================================================================

app = FastAPI(title=APP_TITLE)

# Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Register routers
app.include_router(profile_router, prefix="/api/profile")
app.include_router(projects_router, prefix="/api/projects")
app.include_router(config_router, prefix="/api/config")


# =====================================================================
# 5. FRONTEND SERVE + HEALTH CHECK
# =====================================================================

@app.get("/", include_in_schema=False)
def serve_frontend():
    """Serve main website page (master_portfolio.html)."""
    index_path = os.path.join(STATIC_DIR, "master_portfolio.html")
    if not os.path.exists(index_path):
        return {"error": "master_portfolio.html missing — put file inside /static/"}
    return FileResponse(index_path, media_type="text/html")

@app.get("/api/_health")
def health():
    return {"status": "ok"}
