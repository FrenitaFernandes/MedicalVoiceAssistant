from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal

from models.doctor import Doctor
from models.availability import Availability
from models.appointment import Appointment

from routes.doctors import router as doctors_router
from routes.availability import router as availability_router
from routes.appointments import router as appointments_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Medical Voice Assistant")


# -----------------------------
# CORS Configuration
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Create Sample Doctors
# -----------------------------
def create_sample_doctors():
    db = SessionLocal()

    try:
        existing_doctors = db.query(Doctor).count()

        if existing_doctors == 0:
            doctors = [
                Doctor(
                    name="Dr. Sharma",
                    specialty="Cardiology",
                    qualification="MBBS, MD Cardiology",
                    experience=12
                ),
                Doctor(
                    name="Dr. Priya",
                    specialty="Dermatology",
                    qualification="MBBS, MD Dermatology",
                    experience=8
                ),
                Doctor(
                    name="Dr. Kumar",
                    specialty="General Medicine",
                    qualification="MBBS, MD Medicine",
                    experience=10
                ),
                Doctor(
                    name="Dr. Ananya",
                    specialty="Pediatrics",
                    qualification="MBBS, MD Pediatrics",
                    experience=7
                )
            ]

            db.add_all(doctors)
            db.commit()

    finally:
        db.close()


create_sample_doctors()


# -----------------------------
# Create Sample Availability
# -----------------------------
def create_sample_availability():
    db = SessionLocal()

    try:
        existing_slots = db.query(Availability).count()

        if existing_slots == 0:

            sharma = db.query(Doctor).filter(
                Doctor.name == "Dr. Sharma"
            ).first()

            priya = db.query(Doctor).filter(
                Doctor.name == "Dr. Priya"
            ).first()

            kumar = db.query(Doctor).filter(
                Doctor.name == "Dr. Kumar"
            ).first()

            ananya = db.query(Doctor).filter(
                Doctor.name == "Dr. Ananya"
            ).first()

            slots = [

                # Dr. Sharma
                Availability(
                    doctor_id=sharma.id,
                    date="2026-08-16",
                    time="16:00",
                    is_available=True
                ),

                Availability(
                    doctor_id=sharma.id,
                    date="2026-08-16",
                    time="17:00",
                    is_available=True
                ),

                # Dr. Priya
                Availability(
                    doctor_id=priya.id,
                    date="2026-08-16",
                    time="10:00",
                    is_available=True
                ),

                Availability(
                    doctor_id=priya.id,
                    date="2026-08-16",
                    time="11:00",
                    is_available=True
                ),

                # Dr. Kumar
                Availability(
                    doctor_id=kumar.id,
                    date="2026-08-16",
                    time="14:00",
                    is_available=True
                ),

                Availability(
                    doctor_id=kumar.id,
                    date="2026-08-16",
                    time="15:00",
                    is_available=True
                ),

                # Dr. Ananya
                Availability(
                    doctor_id=ananya.id,
                    date="2026-08-16",
                    time="18:00",
                    is_available=True
                ),

                Availability(
                    doctor_id=ananya.id,
                    date="2026-08-16",
                    time="19:00",
                    is_available=True
                )
            ]

            db.add_all(slots)
            db.commit()

    finally:
        db.close()


create_sample_availability()


# -----------------------------
# Home API
# -----------------------------
@app.get("/")
def home():
    return {
        "message": "Medical Voice Assistant Backend is running"
    }


# -----------------------------
# Include Routers
# -----------------------------
app.include_router(doctors_router)
app.include_router(availability_router)
app.include_router(appointments_router)