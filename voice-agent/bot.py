import os
import httpx

from dotenv import load_dotenv
from loguru import logger
from datetime import datetime

import socket

_original_getaddrinfo = socket.getaddrinfo

def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(
        host,
        port,
        socket.AF_INET,
        type,
        proto,
        flags,
    )

socket.getaddrinfo = ipv4_only_getaddrinfo

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

from pipecat.frames.frames import LLMRunFrame

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)

from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.llm import GoogleLLMService

from pipecat.services.llm_service import FunctionCallParams

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema

from pipecat.transports.base_transport import (
    BaseTransport,
    TransportParams,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(override=True)

BACKEND_URL = "http://127.0.0.1:8000"


# ============================================================
# BOOK APPOINTMENT
# ============================================================

async def book_appointment(params: FunctionCallParams):

    patient_name = params.arguments.get("patient_name")
    doctor_id = params.arguments.get("doctor_id")
    date = params.arguments.get("date")
    time = params.arguments.get("time")

    logger.info(
        f"Booking appointment: "
        f"{patient_name}, doctor={doctor_id}, "
        f"date={date}, time={time}"
    )

    # Check required information
    if not patient_name or not doctor_id or not date or not time:

        await params.result_callback(
            {
                "success": False,
                "message": "Missing appointment information.",
            }
        )

        return

    try:

        async with httpx.AsyncClient() as client:

            response = await client.post(
                f"{BACKEND_URL}/appointments/book",
                params={
                    "patient_name": patient_name,
                    "doctor_id": int(doctor_id),
                    "date": date,
                    "time": time,
                },
                timeout=10,
            )

        # ----------------------------------------------------
        # BOOKING SUCCESS
        # ----------------------------------------------------

        if response.status_code == 200:

            result = response.json()

            logger.info(
                f"Appointment booked: {result}"
            )

            await params.result_callback(
                {
                    "success": True,
                    "message": result.get(
                        "message",
                        "Appointment booked successfully.",
                    ),
                    "appointment_id": result.get(
                        "appointment_id"
                    ),
                    "patient_name": result.get(
                        "patient_name"
                    ),
                    "doctor": result.get(
                        "doctor"
                    ),
                    "specialty": result.get(
                        "specialty"
                    ),
                    "date": result.get(
                        "date"
                    ),
                    "time": result.get(
                        "time"
                    ),
                    "status": result.get(
                        "status"
                    ),
                }
            )

        # ----------------------------------------------------
        # BOOKING FAILED
        # ----------------------------------------------------

        else:

            try:

                error_data = response.json()

                error_message = error_data.get(
                    "detail",
                    "Unable to book the appointment.",
                )

            except Exception:

                error_message = (
                    "Unable to book the appointment."
                )

            await params.result_callback(
                {
                    "success": False,
                    "message": error_message,
                }
            )

    except Exception as e:

        logger.error(
            f"Booking API error: {e}"
        )

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "The appointment service is "
                    "currently unavailable."
                ),
            }
        )


        # ============================================================
# CHECK AVAILABILITY
# ============================================================

async def check_availability(params: FunctionCallParams):
    doctor_id = params.arguments.get("doctor_id")
    date = params.arguments.get("date")
    time = params.arguments.get("time")
    

     # Correct an incorrect year for today's month/day
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        today = datetime.now()

        if (
            parsed_date.month == today.month
            and parsed_date.day == today.day
            and parsed_date.year != today.year
        ):
            date = f"{today.year}-{parsed_date.month:02d}-{parsed_date.day:02d}"
            logger.info(f"Corrected date year to current year: {date}")

    except (ValueError, TypeError):
        pass

    logger.info(
        f"Checking availability: doctor={doctor_id}, "
        f"date={date}, time={time}"
    )

    if not doctor_id or not date or not time:
        await params.result_callback(
            {
                "success": False,
                "available": False,
                "message": "Doctor, date, and time are required."
            }
        )
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_URL}/availability/",
                params={
                    "doctor_id": int(doctor_id),
                    "date": date,
                    "time": time,
                },
                timeout=10,
            )

        if response.status_code == 200:
            result = response.json()

            logger.info(
                f"Availability result: {result}"
            )

            await params.result_callback(
                {
                    "success": True,
                    "available": result.get(
                        "available",
                        False
                    ),
                    "doctor_id": result.get(
                        "doctor_id",
                        doctor_id
                    ),
                    "date": result.get(
                        "date",
                        date
                    ),
                    "time": result.get(
                        "time",
                        time
                    ),
                    "message": result.get(
                        "message",
                        (
                            "The requested slot is available."
                            if result.get("available")
                            else
                            "The requested slot is not available."
                        )
                    ),
                }
            )

        else:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "detail",
                    "Unable to check availability."
                )
            except Exception:
                error_message = "Unable to check availability."

            await params.result_callback(
                {
                    "success": False,
                    "available": False,
                    "message": error_message,
                }
            )

    except Exception as e:
        logger.error(
            f"Availability API error: {e}"
        )

        await params.result_callback(
            {
                "success": False,
                "available": False,
                "message": (
                    "The availability service is "
                    "currently unavailable."
                ),
            }
        )




# ============================================================
# CANCELLATION STATE
# ============================================================

pending_cancellation_id = None


# ============================================================
# REQUEST CANCELLATION
# ============================================================

async def request_cancellation(params: FunctionCallParams):

    global pending_cancellation_id

    appointment_id = params.arguments.get(
        "appointment_id"
    )

    logger.info(
        f"Cancellation requested for appointment: "
        f"{appointment_id}"
    )

    if not appointment_id:

        await params.result_callback(
            {
                "success": False,
                "message": "Please provide the appointment ID.",
            }
        )

        return

    try:

        pending_cancellation_id = int(
            appointment_id
        )

    except (TypeError, ValueError):

        await params.result_callback(
            {
                "success": False,
                "message": "The appointment ID must be a number.",
            }
        )

        return

    # This function DOES NOT cancel.
    # It only prepares cancellation.

    await params.result_callback(
        {
            "success": True,
            "requires_confirmation": True,
            "appointment_id": pending_cancellation_id,
            "message": (
                f"Appointment {pending_cancellation_id} "
                "is ready for cancellation. "
                "The appointment has NOT been cancelled. "
                "Ask the user for explicit confirmation "
                "before calling confirm_cancellation."
            ),
        }
    )


# ============================================================
# CONFIRM CANCELLATION
# ============================================================

async def confirm_cancellation(params: FunctionCallParams):

    global pending_cancellation_id

    appointment_id = params.arguments.get(
        "appointment_id"
    )

    confirmation = params.arguments.get(
        "confirmation"
    )

    logger.info(
        f"Cancellation confirmation: "
        f"appointment={appointment_id}, "
        f"confirmation={confirmation}"
    )

    # --------------------------------------------------------
    # Check pending cancellation
    # --------------------------------------------------------

    if pending_cancellation_id is None:

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "There is no appointment waiting "
                    "for cancellation confirmation."
                ),
            }
        )

        return

    # --------------------------------------------------------
    # Check confirmation
    # --------------------------------------------------------

    if confirmation is not True:

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "Cancellation was not confirmed. "
                    "Do not cancel the appointment."
                ),
            }
        )

        return

    # --------------------------------------------------------
    # Check appointment ID
    # --------------------------------------------------------

    try:

        if int(appointment_id) != pending_cancellation_id:

            await params.result_callback(
                {
                    "success": False,
                    "message": (
                        "The appointment ID does not match "
                        "the appointment awaiting confirmation."
                    ),
                }
            )

            return

    except (TypeError, ValueError):

        await params.result_callback(
            {
                "success": False,
                "message": "Invalid appointment ID.",
            }
        )

        return

    appointment_id = pending_cancellation_id

    logger.info(
        f"Confirmed cancellation for appointment: "
        f"{appointment_id}"
    )

    # --------------------------------------------------------
    # Call backend cancellation API
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient() as client:

            response = await client.put(
                f"{BACKEND_URL}/appointments/"
                f"{appointment_id}/cancel",
                timeout=10,
            )

        # ----------------------------------------------------
        # CANCELLATION SUCCESS
        # ----------------------------------------------------

        if response.status_code == 200:

            result = response.json()

            logger.info(
                f"Appointment cancelled: {result}"
            )

            pending_cancellation_id = None

            await params.result_callback(
                {
                    "success": True,
                    "message": result.get(
                        "message",
                        "Appointment cancelled successfully.",
                    ),
                    "appointment_id": result.get(
                        "appointment_id"
                    ),
                    "status": result.get(
                        "status"
                    ),
                }
            )

        # ----------------------------------------------------
        # CANCELLATION FAILED
        # ----------------------------------------------------

        else:

            try:

                error_data = response.json()

                error_message = error_data.get(
                    "detail",
                    "Unable to cancel the appointment.",
                )

            except Exception:

                error_message = (
                    "Unable to cancel the appointment."
                )

            await params.result_callback(
                {
                    "success": False,
                    "message": error_message,
                }
            )

    except Exception as e:

        logger.error(
            f"Cancellation API error: {e}"
        )

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "The appointment service is "
                    "currently unavailable."
                ),
            }
        )


# ============================================================
# RESCHEDULE STATE
# ============================================================

pending_reschedule = None


# ============================================================
# REQUEST RESCHEDULE
# ============================================================

async def request_reschedule(params: FunctionCallParams):

    global pending_reschedule

    appointment_id = params.arguments.get(
        "appointment_id"
    )

    new_date = params.arguments.get(
        "new_date"
    )

    new_time = params.arguments.get(
        "new_time"
    )

    logger.info(
        f"Reschedule requested: "
        f"appointment={appointment_id}, "
        f"new_date={new_date}, "
        f"new_time={new_time}"
    )

    # --------------------------------------------------------
    # Validate appointment ID
    # --------------------------------------------------------

    if not appointment_id:

        await params.result_callback(
            {
                "success": False,
                "message": "Please provide the appointment ID.",
            }
        )

        return

    try:

        appointment_id = int(
            appointment_id
        )

    except (TypeError, ValueError):

        await params.result_callback(
            {
                "success": False,
                "message": "The appointment ID must be a number.",
            }
        )

        return

    # --------------------------------------------------------
    # Validate date and time
    # --------------------------------------------------------

    if not new_date:

        await params.result_callback(
            {
                "success": False,
                "message": "Please provide the new appointment date.",
            }
        )

        return

    if not new_time:

        await params.result_callback(
            {
                "success": False,
                "message": "Please provide the new appointment time.",
            }
        )

        return

    # --------------------------------------------------------
    # Save pending reschedule
    # --------------------------------------------------------

    pending_reschedule = {
        "appointment_id": appointment_id,
        "new_date": new_date,
        "new_time": new_time,
    }

    await params.result_callback(
        {
            "success": True,
            "requires_confirmation": True,
            "appointment_id": appointment_id,
            "new_date": new_date,
            "new_time": new_time,
            "message": (
                f"Appointment {appointment_id} is ready "
                f"to be rescheduled to {new_date} "
                f"at {new_time}. "
                "The appointment has NOT been changed yet. "
                "Ask the user for explicit confirmation "
                "before calling confirm_reschedule."
            ),
        }
    )


# ============================================================
# CONFIRM RESCHEDULE
# ============================================================

async def confirm_reschedule(params: FunctionCallParams):

    global pending_reschedule

    appointment_id = params.arguments.get(
        "appointment_id"
    )

    confirmation = params.arguments.get(
        "confirmation"
    )

    logger.info(
        f"Reschedule confirmation: "
        f"appointment={appointment_id}, "
        f"confirmation={confirmation}"
    )

    # --------------------------------------------------------
    # Check pending reschedule
    # --------------------------------------------------------

    if pending_reschedule is None:

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "There is no appointment waiting "
                    "for rescheduling confirmation."
                ),
            }
        )

        return

    # --------------------------------------------------------
    # Check confirmation
    # --------------------------------------------------------

    if confirmation is not True:

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "Rescheduling was not confirmed. "
                    "Do not change the appointment."
                ),
            }
        )

        return

    # --------------------------------------------------------
    # Check appointment ID
    # --------------------------------------------------------

    try:

        if (
            int(appointment_id)
            != pending_reschedule["appointment_id"]
        ):

            await params.result_callback(
                {
                    "success": False,
                    "message": (
                        "The appointment ID does not match "
                        "the appointment awaiting "
                        "rescheduling confirmation."
                    ),
                }
            )

            return

    except (TypeError, ValueError):

        await params.result_callback(
            {
                "success": False,
                "message": "Invalid appointment ID.",
            }
        )

        return

    # --------------------------------------------------------
    # Get saved values
    # --------------------------------------------------------

    appointment_id = pending_reschedule[
        "appointment_id"
    ]

    new_date = pending_reschedule[
        "new_date"
    ]

    new_time = pending_reschedule[
        "new_time"
    ]

    logger.info(
        f"Confirmed reschedule: "
        f"appointment={appointment_id}, "
        f"new_date={new_date}, "
        f"new_time={new_time}"
    )

    # --------------------------------------------------------
    # Call backend reschedule API
    # --------------------------------------------------------

    try:

        async with httpx.AsyncClient() as client:

            response = await client.put(
                f"{BACKEND_URL}/appointments/"
                f"{appointment_id}/reschedule",
                params={
                    "new_date": new_date,
                    "new_time": new_time,
                },
                timeout=10,
            )

        # ----------------------------------------------------
        # RESCHEDULE SUCCESS
        # ----------------------------------------------------

        if response.status_code == 200:

            result = response.json()

            logger.info(
                f"Appointment rescheduled: {result}"
            )

            # Clear pending state
            pending_reschedule = None

            await params.result_callback(
                {
                    "success": True,
                    "message": result.get(
                        "message",
                        "Appointment rescheduled successfully.",
                    ),
                    "appointment_id": result.get(
                        "appointment_id"
                    ),
                    "patient_name": result.get(
                        "patient_name"
                    ),
                    "doctor_id": result.get(
                        "doctor_id"
                    ),
                    "new_date": result.get(
                        "new_date"
                    ),
                    "new_time": result.get(
                        "new_time"
                    ),
                    "status": result.get(
                        "status"
                    ),
                }
            )

        # ----------------------------------------------------
        # RESCHEDULE FAILED
        # ----------------------------------------------------

        else:

            try:

                error_data = response.json()

                error_message = error_data.get(
                    "detail",
                    "Unable to reschedule the appointment.",
                )

            except Exception:

                error_message = (
                    "Unable to reschedule the appointment."
                )

            await params.result_callback(
                {
                    "success": False,
                    "message": error_message,
                }
            )

    except Exception as e:

        logger.error(
            f"Reschedule API error: {e}"
        )

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "The appointment service is "
                    "currently unavailable."
                ),
            }
        )


# ============================================================
# VOICE AGENT
# ============================================================

async def run_bot(
    transport: BaseTransport,
    runner_args: RunnerArguments,
):

    logger.info(
        "Starting Medical Voice Assistant"
    )

    # ========================================================
    # SPEECH TO TEXT
    # ========================================================

    stt = DeepgramSTTService(
        api_key=os.getenv(
            "DEEPGRAM_API_KEY"
        )
    )

    # ========================================================
    # TEXT TO SPEECH
    # ========================================================

    tts = CartesiaTTSService(
        api_key=os.getenv(
            "CARTESIA_API_KEY"
        ),
        voice_id=(
            "71a7ad14-091c-4e8e-a314-022ece01c121"
        ),
    )



        # ========================================================
    # AVAILABILITY FUNCTION SCHEMA
    # ========================================================

    availability_function = FunctionSchema(
        name="check_availability",
        description=(
            "Check whether a specific doctor appointment slot "
            "is available. Always use this before booking or "
            "rescheduling when the doctor, date, and time are known."
        ),
        properties={
            "doctor_id": {
                "type": "integer",
                "description": "The ID of the doctor.",
            },
            "date": {
                "type": "string",
                "description": (
                    "Appointment date in YYYY-MM-DD format."
                ),
            },
            "time": {
                "type": "string",
                "description": (
                    "Appointment time in HH:MM 24-hour format."
                ),
            },
        },
        required=[
            "doctor_id",
            "date",
            "time",
        ],
    )
    # ========================================================
    # BOOKING FUNCTION SCHEMA
    # ========================================================

    book_function = FunctionSchema(

        name="book_appointment",

        description=(
            "Book a doctor appointment ONLY after "
            "the patient has provided their name, "
            "doctor ID, date, time, and explicitly "
            "confirmed the appointment."
        ),

        properties={

            "patient_name": {
                "type": "string",
                "description": (
                    "The patient's full name."
                ),
            },

            "doctor_id": {
                "type": "integer",
                "description": (
                    "The ID of the doctor."
                ),
            },

            "date": {
                "type": "string",
                "description": (
                    "Appointment date in "
                    "YYYY-MM-DD format."
                ),
            },

            "time": {
                "type": "string",
                "description": (
                    "Appointment time in "
                    "HH:MM 24-hour format."
                ),
            },
        },

        required=[
            "patient_name",
            "doctor_id",
            "date",
            "time",
        ],
    )

    # ========================================================
    # REQUEST CANCELLATION FUNCTION SCHEMA
    # ========================================================

    request_cancel_function = FunctionSchema(

        name="request_cancellation",

        description=(
            "Start the cancellation process for an "
            "existing appointment. This function DOES NOT "
            "cancel the appointment. It only records the "
            "appointment ID and asks the user for "
            "confirmation."
        ),

        properties={

            "appointment_id": {
                "type": "integer",
                "description": (
                    "The ID of the appointment "
                    "the user wants to cancel."
                ),
            },
        },

        required=[
            "appointment_id",
        ],
    )

    # ========================================================
    # CONFIRM CANCELLATION FUNCTION SCHEMA
    # ========================================================

    confirm_cancel_function = FunctionSchema(

        name="confirm_cancellation",

        description=(
            "Actually cancel an appointment ONLY after "
            "the user explicitly confirms cancellation. "
            "The confirmation value must be true."
        ),

        properties={

            "appointment_id": {
                "type": "integer",
                "description": (
                    "The appointment ID waiting "
                    "for cancellation."
                ),
            },

            "confirmation": {
                "type": "boolean",
                "description": (
                    "Must be true ONLY when the user "
                    "explicitly confirms cancellation."
                ),
            },
        },

        required=[
            "appointment_id",
            "confirmation",
        ],
    )

    # ========================================================
    # REQUEST RESCHEDULE FUNCTION SCHEMA
    # ========================================================

    request_reschedule_function = FunctionSchema(

        name="request_reschedule",

        description=(
            "Start the rescheduling process for an existing "
            "appointment. This function DOES NOT change the "
            "appointment. It only stores the appointment ID, "
            "new date, and new time and asks the user for "
            "confirmation."
        ),

        properties={

            "appointment_id": {
                "type": "integer",
                "description": (
                    "The ID of the existing appointment."
                ),
            },

            "new_date": {
                "type": "string",
                "description": (
                    "The new appointment date in "
                    "YYYY-MM-DD format."
                ),
            },

            "new_time": {
                "type": "string",
                "description": (
                    "The new appointment time in "
                    "HH:MM 24-hour format."
                ),
            },
        },

        required=[
            "appointment_id",
            "new_date",
            "new_time",
        ],
    )

    # ========================================================
    # CONFIRM RESCHEDULE FUNCTION SCHEMA
    # ========================================================

    confirm_reschedule_function = FunctionSchema(

        name="confirm_reschedule",

        description=(
            "Actually reschedule an appointment ONLY after "
            "the user explicitly confirms the new date and "
            "time. The confirmation value must be true."
        ),

        properties={

            "appointment_id": {
                "type": "integer",
                "description": (
                    "The appointment ID waiting "
                    "for rescheduling."
                ),
            },

            "confirmation": {
                "type": "boolean",
                "description": (
                    "Must be true ONLY when the user "
                    "explicitly confirms the rescheduling."
                ),
            },
        },

        required=[
            "appointment_id",
            "confirmation",
        ],
    )

    # ========================================================
    # GEMINI
    # ========================================================

    llm = GoogleLLMService(

        api_key=os.getenv(
            "GEMINI_API_KEY"
        ),

        model="gemini-3.5-flash-lite",
    )

    # ========================================================
    # TOOLS
    # ========================================================

    tools = ToolsSchema(
    standard_tools=[
        availability_function,
        book_function,
        request_cancel_function,
        confirm_cancel_function,
        request_reschedule_function,
        confirm_reschedule_function,
    ]
)

    # ========================================================
    # REGISTER FUNCTIONS
    # ========================================================


    llm.register_function(
        "check_availability",
        check_availability,
    )
    llm.register_function(
        "book_appointment",
        book_appointment,
    )

    llm.register_function(
        "request_cancellation",
        request_cancellation,
    )

    llm.register_function(
        "confirm_cancellation",
        confirm_cancellation,
    )

    llm.register_function(
        "request_reschedule",
        request_reschedule,
    )

    llm.register_function(
        "confirm_reschedule",
        confirm_reschedule,
    )

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    messages = [

        {
            "role": "system",

            "content": """

You are a friendly medical appointment assistant.

Your job is to help users book, cancel, and reschedule
doctor appointments.

IMPORTANT RULES:

1. Speak clearly and briefly.

2. Ask for missing information one thing at a time.

3. You can help with:
   - Booking appointments
   - Cancelling appointments
   - Rescheduling appointments

============================================================
BOOKING
============================================================

4. For booking you need:

   - patient name
   - doctor ID
   - appointment date
   - appointment time

5. Available doctors:

   Dr. Sharma - ID 1 - Cardiology

   Dr. Priya - ID 2 - Dermatology

   Dr. Kumar - ID 3 - General Medicine

   Dr. Ananya - ID 4 - Pediatrics

6. If the user asks for a specialist,
   choose the matching doctor from this list.

7. Never invent doctor IDs.

8. Always ask for confirmation before booking.

9. Do NOT call book_appointment until the
   user explicitly confirms the appointment.

10. Do not claim an appointment is booked
    until book_appointment returns success.

11. If booking fails, tell the user the reason.

12. After successful booking, confirm:

    - patient name
    - doctor
    - specialty
    - date
    - time
    - appointment ID

============================================================
CANCELLATION
============================================================

13. If the user wants to cancel an appointment,
    ask for the appointment ID if they have not
    provided it.

14. When the user provides an appointment ID,
    call request_cancellation.

15. request_cancellation NEVER cancels
    the appointment.

16. After request_cancellation returns,
    ask the user:

    "Would you like me to cancel appointment ID X?"

17. NEVER call confirm_cancellation in the same
    turn as request_cancellation.

18. ONLY call confirm_cancellation after the user
    explicitly confirms the cancellation.

19. Examples of explicit confirmation:

    "Yes"

    "Yes, cancel it"

    "Please cancel it"

    "I confirm"

    "Go ahead and cancel"

20. If the user says no, do NOT call
    confirm_cancellation.

21. When calling confirm_cancellation:

    appointment_id must be the appointment ID
    that the user previously provided.

    confirmation must be true ONLY after
    explicit user confirmation.

22. Do not claim an appointment is cancelled
    until confirm_cancellation returns success.

23. If cancellation fails, tell the user the reason.

24. After successful cancellation, tell the user
    that the appointment was cancelled.

25. Never invent appointment IDs.

============================================================
RESCHEDULING
============================================================

26. If the user wants to reschedule an appointment,
    DO NOT tell them that the appointment must first
    be cancelled and then booked again.

27. The system has a dedicated rescheduling operation.

28. Ask for the appointment ID if the user has not
    provided it.

29. Ask for the new date if it is missing.

30. Ask for the new time if it is missing.

31. Dates must use YYYY-MM-DD format.

32. Times must use HH:MM 24-hour format.

33. Once you have:

    - appointment ID
    - new date
    - new time

    call request_reschedule.

34. request_reschedule DOES NOT change the appointment.

35. After request_reschedule returns successfully,
    tell the user the new appointment details and ask
    for explicit confirmation.

36. For example:

    "Your appointment ID 4 will be rescheduled to
     August 16 at 11:00. Would you like me to
     confirm this change?"

37. NEVER call confirm_reschedule in the same turn
    as request_reschedule.

38. ONLY call confirm_reschedule after the user
    explicitly confirms.

39. Examples of explicit rescheduling confirmation:

    "Yes"

    "Yes, reschedule it"

    "Please reschedule it"

    "I confirm"

    "Go ahead"

    "Yes, that's correct"

40. If the user says no, do NOT call
    confirm_reschedule.

41. When calling confirm_reschedule:

    appointment_id must be the appointment ID
    previously provided by the user.

    confirmation must be true ONLY after
    explicit user confirmation.

42. Do not claim the appointment was rescheduled
    until confirm_reschedule returns success.

43. If rescheduling fails, tell the user the reason.

44. After successful rescheduling, tell the user:

    - appointment ID
    - new date
    - new time
    - that the appointment was successfully rescheduled

45. NEVER cancel the appointment as part of
    the rescheduling process.

46. NEVER book a new appointment as part of
    the rescheduling process.

47. Use the dedicated reschedule operation.

48. Never invent appointment IDs.

49. Before booking or rescheduling, when the doctor,
    date, and time are known, call check_availability.

50. If check_availability returns available=false,
    do NOT call book_appointment or confirm_reschedule
    for that slot.

51. Tell the user that the requested slot is unavailable
    and ask for another time.

52. If check_availability returns available=true,
    continue with the normal confirmation process.

53. Never claim a slot is available unless
    check_availability returns available=true.

54. Never invent availability information.

============================================================
DATE HANDLING
============================================================

55. The current date is August 16, 2026.

56. If the user says "today", use 2026-08-16.

57. If the user gives a month and day without a year,
    use the current year 2026.

58. Never use 2025 for an appointment date unless
    the user explicitly says 2025.

59. Always send appointment dates to functions in
    YYYY-MM-DD format.

"""
        }
    ]

    # ========================================================
    # LLM CONTEXT
    # ========================================================

    context = LLMContext(
        messages=messages,
        tools=tools,
    )

    user_aggregator, assistant_aggregator = (
        LLMContextAggregatorPair(context)
    )

    # ========================================================
    # VOICE PIPELINE
    # ========================================================

    pipeline = Pipeline(
        [
            transport.input(),

            stt,

            user_aggregator,

            llm,

            tts,

            transport.output(),

            assistant_aggregator,
        ]
    )

    # ========================================================
    # PIPELINE TASK
    # ========================================================

    task = PipelineTask(

        pipeline,

        params=PipelineParams(

            enable_metrics=True,

            enable_usage_metrics=True,
        ),
    )

    # ========================================================
    # CLIENT CONNECTED
    # ========================================================

    @transport.event_handler(
        "on_client_connected"
    )
    async def on_client_connected(
        transport,
        client,
    ):

        logger.info(
            "Client connected"
        )

        await task.queue_frames(
            [
                LLMRunFrame()
            ]
        )

    # ========================================================
    # CLIENT DISCONNECTED
    # ========================================================

    @transport.event_handler(
        "on_client_disconnected"
    )
    async def on_client_disconnected(
        transport,
        client,
    ):

        logger.info(
            "Client disconnected"
        )

        await task.cancel()

    # ========================================================
    # PIPELINE RUNNER
    # ========================================================

    runner = PipelineRunner(
        handle_sigint=runner_args.handle_sigint
    )

    await runner.run(task)


# ============================================================
# BOT
# ============================================================

async def bot(
    runner_args: RunnerArguments,
):

    transport_params = {

        "webrtc": lambda: TransportParams(

            audio_in_enabled=True,

            audio_out_enabled=True,

            vad_analyzer=SileroVADAnalyzer(

                params=VADParams(

                    stop_secs=0.2
                )
            ),
        )
    }

    transport = await create_transport(
        runner_args,
        transport_params,
    )

    await run_bot(
        transport,
        runner_args,
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    from pipecat.runner.run import main

    main()