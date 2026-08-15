from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.availability import Availability


router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)


@router.get("/")
def check_availability(
    doctor_id: int = Query(...),
    date: str = Query(...),
    time: str = Query(...),
    db: Session = Depends(get_db)
):
    slot = (
        db.query(Availability)
        .filter(
            Availability.doctor_id == doctor_id,
            Availability.date == date,
            Availability.time == time
        )
        .first()
    )

    if not slot:
        return {
            "available": False,
            "message": "No availability information found for this slot."
        }

    return {
        "available": slot.is_available,
        "doctor_id": slot.doctor_id,
        "date": slot.date,
        "time": slot.time
    }