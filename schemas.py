from pydantic import BaseModel, EmailStr


class StudentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    skills: str | None = None
    resume: str | None = None