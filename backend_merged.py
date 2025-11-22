import os
import json
import uuid
import shutil
from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# =====================================================================
# 1. Configuration and Base Setup
# =====================================================================

APP_TITLE = "Pradipta Portfolio Backend"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder structure
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_DIR = os.path.join(BASE_DIR, "db")

# JSON storage
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
    """Loads JSON with fallback defaults if file doesn't exist or invalid."""
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
            return {"skills": {}, "certifications": [], "offerings": [], "contact_info": {}}
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            return {} if not content.strip() else json.loads(content)
    except Exception:
        return {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_upload_file(file: UploadFile, folder: str):
    """Save uploaded file with UUID filename and return (filename, filepath)."""
    os.makedirs(folder, exist_ok=True)
    parts = file.filename.split(".")
    ext = parts[-1] if len(parts) > 1 else ""
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename, filepath

# =====================================================================
# 3. Profile Router
# =====================================================================

profile_router = APIRouter()

@profile_router.get("/")
def get_profile():
    return load_json(PROFILE_JSON)

@profile_router.post("/update")
def update_profile(data: dict):
    profile = load_json(PROFILE_JSON)
    profile.update({k: v for k, v in data.items() if v is not None})
    save_json(PROFILE_JSON, profile)
    return {"ok": True, "profile": profile}

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

# =====================================================================
# 4. Projects Router
# =====================================================================

projects_router = APIRouter()

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
    new_projects = [p for p in projects if p.get("id") != project_id]
    if len(projects) == len(new_projects):
        raise HTTPException(status_code=404, detail="Project not found")
    save_json(PROJECTS_JSON, new_projects)
    return {"ok": True}

@projects_router.post("/upload-image/{project_id}")
async def upload_project_image(project_id: str, file: UploadFile = File(...)):
    filename, _ = save_upload_file(file, PROJECTS_DIR)
    projects = load_json(PROJECTS_JSON)
    updated = False
    for p in projects:
        if p.get("id") == project_id:
            p["imagePath"] = f"/uploads/projects/{filename}"
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    save_json(PROJECTS_JSON, projects)
    return {"ok": True, "path": f"/uploads/projects/{filename}"}

# =====================================================================
# 5. Config Router
# =====================================================================

config_router = APIRouter()

@config_router.get("/")
def get_config():
    return load_json(CONFIG_JSON)

@config_router.post("/update")
def update_config(data: dict):
    save_json(CONFIG_JSON, data)
    return {"ok": True}

# =====================================================================
# 6. FastAPI App initialization
# =====================================================================

app = FastAPI(title=APP_TITLE)

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://pradiptachandra.in",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(config_router, prefix="/api/config", tags=["Config"])

@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse(
            "<h1>⚠ index.html missing</h1><p>Place your frontend file inside the /static/ folder.</p>",
            status_code=404
        )
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/_health")
def health():
    return {"status": "running"}
