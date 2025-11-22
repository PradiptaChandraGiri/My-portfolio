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

# BASE_DIR = folder where this file (backend_merged.py) lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Essential directories
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_DIR = os.path.join(BASE_DIR, "db")

# JSON “DB” files
PROFILE_JSON = os.path.join(DB_DIR, "profile.json")
PROJECTS_JSON = os.path.join(DB_DIR, "projects.json")
CONFIG_JSON = os.path.join(DB_DIR, "config.json")

# Upload sub-folders
PROFILE_DIR = os.path.join(UPLOADS_DIR, "profile")
PROJECTS_DIR = os.path.join(UPLOADS_DIR, "projects")

# Make sure folders exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)


# =====================================================================
# 2. Utility Functions  (JSON + File helpers)
# =====================================================================

def load_json(path: str):
    """Load JSON from path. If file missing, return sensible defaults."""
    if not os.path.exists(path):
        # Initialize JSON files with empty data if missing
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
        elif path.endswith("projects.json"):
            return []
        elif path.endswith("config.json"):
            return {
                "skills": {},
                "certifications": [],
                "offerings": [],
                "contact_info": {}
            }
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                # Empty file
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
                elif path.endswith("projects.json"):
                    return []
                elif path.endswith("config.json"):
                    return {
                        "skills": {},
                        "certifications": [],
                        "offerings": [],
                        "contact_info": {}
                    }
                return {}
            return json.loads(content)
    except Exception:
        # Corrupted JSON etc.
        return {}


def save_json(path: str, data):
    """Save Python data (dict/list) to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_upload_file(file: UploadFile, folder: str):
    """
    Save uploaded file into the given folder.
    Returns (filename, full_path).
    """
    os.makedirs(folder, exist_ok=True)

    parts = file.filename.split(".")
    extension = parts[-1] if len(parts) > 1 else ""
    filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename, filepath


# =====================================================================
# 3. Profile Router - /api/profile
# =====================================================================

profile_router = APIRouter()


@profile_router.get("/")
def get_profile():
    """Return profile JSON for frontend."""
    data = load_json(PROFILE_JSON)
    return data


@profile_router.post("/update")
def update_profile(data: dict):
    """
    Update profile JSON.
    Frontend POSTs fields: name, tagline, about, email, linkedin, github,
    photo_path, resume_path (any missing can be null).
    """
    current = load_json(PROFILE_JSON)
    # Only update keys that are not None
    for k, v in data.items():
        if v is not None:
            current[k] = v

    save_json(PROFILE_JSON, current)
    return {"ok": True, "profile": current}


@profile_router.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """
    Upload profile photo, store in uploads/profile, and
    update profile.json.photo_path with "/uploads/profile/<filename>".
    """
    filename, _ = save_upload_file(file, PROFILE_DIR)

    profile = load_json(PROFILE_JSON)
    profile["photo_path"] = f"/uploads/profile/{filename}"
    save_json(PROFILE_JSON, profile)

    return {"ok": True, "path": profile["photo_path"]}


@profile_router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload resume PDF, store in uploads/profile, and
    update profile.json.resume_path with "/uploads/profile/<filename>".
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF")

    filename, _ = save_upload_file(file, PROFILE_DIR)

    profile = load_json(PROFILE_JSON)
    profile["resume_path"] = f"/uploads/profile/{filename}"
    save_json(PROFILE_JSON, profile)

    return {"ok": True, "path": profile["resume_path"]}


# =====================================================================
# 4. Projects Router - /api/projects
# =====================================================================

projects_router = APIRouter()


@projects_router.get("/")
def get_projects():
    """Return all projects."""
    return load_json(PROJECTS_JSON)


@projects_router.post("/add")
def add_project(data: dict):
    """
    Add a new project.
    Expects:
      - title (str)
      - description (str)
      - techStack (list[str])
      - highlights (list[str])
      - githubUrl (str)
      - demoUrl (str)
      - imagePath (str or null)
    """
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
    """
    Delete a project by ID.
    The frontend sends FormData with field 'project_id'.
    """
    projects = load_json(PROJECTS_JSON)
    new_projects = [p for p in projects if p.get("id") != project_id]

    if len(projects) == len(new_projects):
        raise HTTPException(status_code=404, detail="Project not found")

    save_json(PROJECTS_JSON, new_projects)
    return {"ok": True}


@projects_router.post("/upload-image/{project_id}")
async def upload_project_image(project_id: str, file: UploadFile = File(...)):
    """
    Upload an image for a specific project.
    Saves file under uploads/projects and updates that project's imagePath.
    """
    filename, _ = save_upload_file(file, PROJECTS_DIR)

    projects = load_json(PROJECTS_JSON)
    updated = False

    for p in projects:
        if p.get("id") == project_id:
            p["imagePath"] = f"/uploads/projects/{filename}"
            updated = True
            break

    if not updated:
        # Project id not found
        raise HTTPException(status_code=404, detail="Project not found")

    save_json(PROJECTS_JSON, projects)

    return {
        "ok": True,
        "updated": updated,
        "path": f"/uploads/projects/{filename}",
    }


# =====================================================================
# 5. Config Router - /api/config
# =====================================================================

config_router = APIRouter()


@config_router.get("/")
def get_config():
    """Return config.json (skills, certifications, offerings, contact_info)."""
    return load_json(CONFIG_JSON)


@config_router.post("/update")
def update_config(data: dict):
    """
    Replace config.json with provided data.
    The frontend can send entire config in one POST.
    """
    save_json(CONFIG_JSON, data)
    return {"ok": True}


# =====================================================================
# 6. FastAPI App Setup
# =====================================================================

app = FastAPI(title=APP_TITLE)

# CORS Middleware
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

# Static file mounting (for uploads and static assets)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Register routers
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(projects_router, prefix="/api/projects", tags=["Projects"])
app.include_router(config_router, prefix="/api/config", tags=["Config"])


# =====================================================================
# 7. Frontend Serving + Health Check
# =====================================================================

@app.get("/", include_in_schema=False)
def serve_frontend():
    """
    Serve your main frontend HTML file:
    /static/master_portfolio.html
    """
    index_path = os.path.join(STATIC_DIR, "master_portfolio.html")
    if not os.path.exists(index_path):
        # Helpful message if file missing
        return {
            "error": "master_portfolio.html missing — place your frontend file in /static/master_portfolio.html"
        }
    return FileResponse(index_path, media_type="text/html")


@app.get("/api/_health")
def health():
    """Simple health check endpoint for testing."""
    return {"status": "ok"}
