from sqlalchemy import Column, Integer, String, Text
from database import Base


# ---------------- STUDENT ----------------

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    skills = Column(String(500), nullable=True)
    resume = Column(String(255), nullable=True)


# ---------------- JOB ----------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(100), nullable=False)
    job_title = Column(String(150), nullable=False)
    location = Column(String(100), nullable=True)
    salary = Column(String(100), nullable=True)
    skills_required = Column(String(500), nullable=True)
    job_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    apply_link = Column(String(500), nullable=True)


# ---------------- APPLICATION ----------------

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False)
    job_id = Column(Integer, nullable=False)
    status = Column(String(50), default="Applied")
    