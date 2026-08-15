from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.doctor import Doctor


router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


@router.get("/")
def get_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).all()

    return doctors