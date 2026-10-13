
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
import jwt

from database import engine, Base, get_db
from models import Student, Job, Application
from schemas import StudentCreate


app = FastAPI(title="Smart Placement System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
Base.metadata.create_all(bind=engine)

# Password and JWT
password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET":
    raise RuntimeError(
        "Please set a new random SECRET_KEY in your .env file."
    )

ALGORITHM = "HS256"
security = HTTPBearer()

# Resume folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# HOME
@app.get("/")
def home():
    return {"message": "Smart Placement System is running"}


# TEST DATABASE
@app.get("/test-db")
def test_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "success",
            "message": "Database connected successfully!"
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed. Check server logs."
        )


# STUDENT REGISTER
@app.post("/register")
def register_student(
    student: StudentCreate,
    db: Session = Depends(get_db)
):
    existing_student = (
        db.query(Student)
        .filter(Student.email == student.email)
        .first()
    )

    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_password = password_hash.hash(student.password)

    new_student = Student(
        name=student.name,
        email=student.email,
        password=hashed_password,
        skills=student.skills,
        resume=student.resume
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return {
        "status": "success",
        "message": "Student registered successfully!",
        "student_id": new_student.id
    }


# STUDENT LOGIN
@app.post("/login")
def login_student(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    student = (
        db.query(Student)
        .filter(Student.email == email)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    try:
        password_valid = password_hash.verify(
            password,
            student.password
        )
    except Exception:
        # Support legacy plain-text passwords and migrate them.
        if student.password == password:
            student.password = password_hash.hash(password)
            db.commit()
            password_valid = True
        else:
            password_valid = False

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = jwt.encode(
        {
            "student_id": student.id,
            "email": student.email
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "status": "success",
        "message": "Login successful!",
        "access_token": token,
        "token_type": "bearer"
    }


# CURRENT STUDENT
def get_current_student(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        student_id = payload.get("student_id")

        if student_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return student


# PROFILE
@app.get("/profile")
def get_profile(
    current_student: Student = Depends(get_current_student)
):
    return {
        "id": current_student.id,
        "name": current_student.name,
        "email": current_student.email,
        "skills": current_student.skills,
        "resume": current_student.resume
    }


# RESUME UPLOAD
@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    file_content = await file.read()

    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file"
        )

    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="PDF size must be 5 MB or less"
        )

    unique_filename = (
        f"{current_student.id}_{uuid.uuid4().hex}.pdf"
    )
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(file_path, "wb") as f:
        f.write(file_content)

    current_student.resume = file_path
    db.commit()
    db.refresh(current_student)

    return {
        "status": "success",
        "message": "Resume uploaded successfully!",
        "filename": unique_filename,
        "path": file_path
    }


# JOB RESPONSE HELPER
def job_to_dict(job):
    return {
        "job_id": job.id,
        "company": job.company,
        "job_title": job.job_title,
        "location": job.location,
        "salary": job.salary,
        "skills_required": job.skills_required,
        "job_type": job.job_type,
        "description": job.description,
        "apply_link": job.apply_link
    }


# ALL JOBS
@app.get("/jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()

    return {
        "status": "success",
        "total_jobs": len(jobs),
        "jobs": [job_to_dict(job) for job in jobs]
    }


# SEARCH JOBS
@app.get("/jobs/search")
def search_jobs(
    keyword: str = "",
    db: Session = Depends(get_db)
):
    search_term = f"%{keyword}%"

    jobs = db.query(Job).filter(
        (Job.company.ilike(search_term)) |
        (Job.job_title.ilike(search_term)) |
        (Job.location.ilike(search_term)) |
        (Job.skills_required.ilike(search_term))
    ).all()

    return {
        "status": "success",
        "keyword": keyword,
        "total_jobs": len(jobs),
        "jobs": [job_to_dict(job) for job in jobs]
    }


# JOB DETAILS
@app.get("/jobs/{job_id}")
def get_job_details(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "status": "success",
        "job": job_to_dict(job)
    }


# CREATE JOB
@app.post("/jobs")
def create_job(
    company: str,
    job_title: str,
    location: str,
    salary: str,
    skills_required: str,
    job_type: str,
    description: str,
    apply_link: str,
    db: Session = Depends(get_db)
):
    new_job = Job(
        company=company,
        job_title=job_title,
        location=location,
        salary=salary,
        skills_required=skills_required,
        job_type=job_type,
        description=description,
        apply_link=apply_link
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return {
        "status": "success",
        "message": "Job added successfully!",
        "job_id": new_job.id
    }


# APPLY FOR JOB
@app.post("/jobs/{job_id}/apply")
def apply_for_job(
    job_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    existing_application = db.query(Application).filter(
        Application.job_id == job_id,
        Application.student_id == current_student.id
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=400,
            detail="You have already applied for this job"
        )

    application = Application(
        job_id=job_id,
        student_id=current_student.id,
        status="Applied"
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "status": "success",
        "message": "Job application submitted successfully!",
        "application_id": application.id,
        "job_id": job_id,
        "student_id": current_student.id,
        "application_status": application.status
    }


# MY APPLICATIONS
@app.get("/my-applications")
def my_applications(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    applications = db.query(Application).filter(
        Application.student_id == current_student.id
    ).all()

    result = []

    for application in applications:
        job = db.query(Job).filter(
            Job.id == application.job_id
        ).first()

        if job:
            result.append({
                "application_id": application.id,
                "job_id": job.id,
                "job_title": job.job_title,
                "company": job.company,
                "location": job.location,
                "salary": job.salary,
                "status": application.status
            })

    return {
        "status": "success",
        "total_applications": len(result),
        "applications": result
    }


# STUDENT DASHBOARD
@app.get("/dashboard")
def student_dashboard(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    applications = db.query(Application).filter(
        Application.student_id == current_student.id
    ).all()

    return {
        "status": "success",
        "student": current_student.name,
        "email": current_student.email,
        "skills": current_student.skills,
        "placement_summary": {
            "total_applications": len(applications),
            "shortlisted": sum(
                app.status == "Shortlisted" for app in applications
            ),
            "selected": sum(
                app.status == "Selected" for app in applications
            ),
            "rejected": sum(
                app.status == "Rejected" for app in applications
            )
        }
    }


# COMPANY DASHBOARD
@app.get("/company-dashboard/{company_name}")
def company_dashboard(
    company_name: str,
    db: Session = Depends(get_db)
):
    jobs = db.query(Job).filter(
        Job.company == company_name
    ).all()

    result = []

    for job in jobs:
        applications = db.query(Application).filter(
            Application.job_id == job.id
        ).all()

        result.append({
            "job_id": job.id,
            "job_title": job.job_title,
            "location": job.location,
            "salary": job.salary,
            "total_applications": len(applications),
            "applications": [
                {
                    "application_id": application.id,
                    "student_id": application.student_id,
                    "status": application.status
                }
                for application in applications
            ]
        })

    return {
        "status": "success",
        "company": company_name,
        "total_jobs": len(result),
        "jobs": result
    }


# JOB APPLICATIONS WITH STUDENT DETAILS
@app.get("/jobs/{job_id}/applications")
def get_job_applications(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    applications = db.query(Application).filter(
        Application.job_id == job_id
    ).all()

    result = []

    for application in applications:
        student = db.query(Student).filter(
            Student.id == application.student_id
        ).first()

        if student:
            result.append({
                "application_id": application.id,
                "student_id": student.id,
                "student_name": student.name,
                "student_email": student.email,
                "student_skills": student.skills,
                "application_status": application.status
            })

    return {
        "status": "success",
        "company": job.company,
        "job_title": job.job_title,
        "applications": result
    }


# UPDATE APPLICATION STATUS
@app.put("/applications/{application_id}/status")
def update_application_status(
    application_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    allowed_status = [
        "Applied",
        "Shortlisted",
        "Rejected",
        "Selected"
    ]

    if status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Status must be Applied, Shortlisted, Rejected, or Selected"
        )

    application.status = status
    db.commit()
    db.refresh(application)

    return {
        "status": "success",
        "message": "Application status updated successfully!",
        "application_id": application.id,
        "new_status": application.status
    }


# UPDATE JOB
@app.put("/jobs/{job_id}")
def update_job(
    job_id: int,
    company: str,
    job_title: str,
    location: str,
    salary: str,
    skills_required: str,
    job_type: str,
    description: str,
    apply_link: str,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    job.company = company
    job.job_title = job_title
    job.location = location
    job.salary = salary
    job.skills_required = skills_required
    job.job_type = job_type
    job.description = description
    job.apply_link = apply_link

    db.commit()
    db.refresh(job)

    return {
        "status": "success",
        "message": "Job updated successfully!",
        "job_id": job.id
    }


# DELETE JOB
@app.delete("/jobs/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    db.query(Application).filter(
        Application.job_id == job_id
    ).delete()

    db.delete(job)
    db.commit()

    return {
        "status": "success",
        "message": "Job deleted successfully!",
        "job_id": job_id
    }
