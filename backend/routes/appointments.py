from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.doctor import Doctor
from models.availability import Availability
from models.appointment import Appointment


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)


# =========================
# BOOK APPOINTMENT
# =========================

@router.post("/book")
def book_appointment(
    patient_name: str,
    doctor_id: int,
    date: str,
    time: str,
    db: Session = Depends(get_db)
):
    # Check doctor
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found."
        )

    # Check availability
    slot = db.query(Availability).filter(
        Availability.doctor_id == doctor_id,
        Availability.date == date,
        Availability.time == time
    ).first()

    if not slot:
        raise HTTPException(
            status_code=400,
            detail="No availability for the requested time."
        )

    if not slot.is_available:
        raise HTTPException(
            status_code=400,
            detail="This appointment slot is already booked."
        )

    # Create appointment
    appointment = Appointment(
        patient_name=patient_name,
        doctor_id=doctor_id,
        date=date,
        time=time,
        status="confirmed"
    )

    db.add(appointment)

    # Make slot unavailable
    slot.is_available = False

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment booked successfully.",
        "appointment_id": appointment.id,
        "patient_name": appointment.patient_name,
        "doctor": doctor.name,
        "specialty": doctor.specialty,
        "date": appointment.date,
        "time": appointment.time,
        "status": appointment.status
    }


# =========================
# CANCEL APPOINTMENT
# =========================

@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found."
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Appointment is already cancelled."
        )

    # Find original slot
    slot = db.query(Availability).filter(
        Availability.doctor_id == appointment.doctor_id,
        Availability.date == appointment.date,
        Availability.time == appointment.time
    ).first()

    # Make slot available again
    if slot:
        slot.is_available = True

    # Cancel appointment
    appointment.status = "cancelled"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment cancelled successfully.",
        "appointment_id": appointment.id,
        "status": appointment.status
    }


# =========================
# RESCHEDULE APPOINTMENT
# =========================

@router.put("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int,
    new_date: str,
    new_time: str,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found."
        )

    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule a cancelled appointment."
        )

    # Check new slot
    new_slot = db.query(Availability).filter(
        Availability.doctor_id == appointment.doctor_id,
        Availability.date == new_date,
        Availability.time == new_time
    ).first()

    if not new_slot:
        raise HTTPException(
            status_code=400,
            detail="No availability for the requested new time."
        )

    if not new_slot.is_available:
        raise HTTPException(
            status_code=400,
            detail="The requested new time is already booked."
        )

    # Free old slot
    old_slot = db.query(Availability).filter(
        Availability.doctor_id == appointment.doctor_id,
        Availability.date == appointment.date,
        Availability.time == appointment.time
    ).first()

    if old_slot:
        old_slot.is_available = True

    # Occupy new slot
    new_slot.is_available = False

    # Update appointment
    appointment.date = new_date
    appointment.time = new_time
    appointment.status = "rescheduled"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment rescheduled successfully.",
        "appointment_id": appointment.id,
        "patient_name": appointment.patient_name,
        "doctor_id": appointment.doctor_id,
        "new_date": appointment.date,
        "new_time": appointment.time,
        "status": appointment.status
    }