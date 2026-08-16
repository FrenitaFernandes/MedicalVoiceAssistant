import os
import httpx

from dotenv import load_dotenv
from loguru import logger

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

    # Validate information
    if not patient_name or not doctor_id or not date or not time:

        await params.result_callback(
            {
                "success": False,
                "message": "Missing appointment information."
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

        # Successful booking
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
                        "Appointment booked successfully."
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

        else:

            try:

                error_data = response.json()

                error_message = error_data.get(
                    "detail",
                    "Unable to book the appointment."
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
# CANCEL APPOINTMENT
# ============================================================

async def cancel_appointment(params: FunctionCallParams):

    appointment_id = params.arguments.get(
        "appointment_id"
    )

    logger.info(
        f"Cancelling appointment: {appointment_id}"
    )

    # Validate appointment ID
    if not appointment_id:

        await params.result_callback(
            {
                "success": False,
                "message": (
                    "Please provide the appointment ID."
                )
            }
        )

        return

    try:

        async with httpx.AsyncClient() as client:

            response = await client.put(
                f"{BACKEND_URL}/appointments/"
                f"{int(appointment_id)}/cancel",

                timeout=10,
            )

        # Successful cancellation
        if response.status_code == 200:

            result = response.json()

            logger.info(
                f"Appointment cancelled: {result}"
            )

            await params.result_callback(
                {
                    "success": True,

                    "message": result.get(
                        "message",
                        "Appointment cancelled successfully."
                    ),

                    "appointment_id": result.get(
                        "appointment_id"
                    ),

                    "status": result.get(
                        "status"
                    ),
                }
            )

        else:

            try:

                error_data = response.json()

                error_message = error_data.get(
                    "detail",
                    "Unable to cancel the appointment."
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
    # BOOKING FUNCTION SCHEMA
    # ========================================================

    book_function = FunctionSchema(

        name="book_appointment",

        description=(
            "Book a doctor appointment after the patient "
            "has provided their name, doctor ID, date, "
            "and time."
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
    # CANCELLATION FUNCTION SCHEMA
    # ========================================================

    cancel_function = FunctionSchema(

        name="cancel_appointment",

        description=(
            "Cancel an existing doctor appointment "
            "using the appointment ID."
        ),

        properties={

            "appointment_id": {
                "type": "integer",
                "description": (
                    "The ID of the appointment "
                    "that should be cancelled."
                ),
            },
        },

        required=[
            "appointment_id",
        ],
    )

    # ========================================================
    # GEMINI
    # ========================================================

    llm = GoogleLLMService(

        api_key=os.getenv(
            "GEMINI_API_KEY"
        ),

        # Working free-tier model
        model="gemini-3.5-flash-lite",
    )

    # ========================================================
    # TOOLS
    # ========================================================

    tools = ToolsSchema(
        standard_tools=[
            book_function,
            cancel_function,
        ]
    )

    # Register booking function
    llm.register_function(
        "book_appointment",
        book_appointment,
    )

    # Register cancellation function
    llm.register_function(
        "cancel_appointment",
        cancel_appointment,
    )

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    messages = [

        {
            "role": "system",

            "content": """

You are a friendly medical appointment assistant.

Your job is to help users book and cancel
doctor appointments.

IMPORTANT RULES:

1. Speak clearly and briefly.

2. Ask for missing information one thing
   at a time.

3. You can help with:
   - Booking appointments
   - Cancelling appointments

4. For booking you need:
   - patient name
   - doctor ID
   - appointment date
   - appointment time

5. Do not invent doctor IDs.

6. Available doctors:

   Dr. Sharma - ID 1 - Cardiology

   Dr. Priya - ID 2 - Dermatology

   Dr. Kumar - ID 3 - General Medicine

   Dr. Ananya - ID 4 - Pediatrics

7. If the user asks for a specialist,
   choose the matching doctor from this list.

8. Always ask for confirmation before booking.

9. Do NOT call book_appointment until the
   user explicitly confirms the appointment.

10. Do not claim that an appointment is booked
    until book_appointment returns success.

11. If booking fails, tell the user the reason.

12. After successful booking, confirm:
    - patient name
    - doctor
    - date
    - time
    - appointment ID

13. For cancellation, ask the user for the
    appointment ID if they have not provided it.

14. Before cancelling, confirm that the user
    wants to cancel that appointment.

15. Do NOT call cancel_appointment until the
    user explicitly confirms cancellation.

16. Do not claim that an appointment is cancelled
    until cancel_appointment returns success.

17. If cancellation fails, tell the user the reason.

18. After successful cancellation, tell the user
    that the appointment was cancelled.

19. Never invent appointment IDs.

20. Never invent availability information.

Be concise and natural because this is a
voice conversation.

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
        client
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
        client
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
    runner_args: RunnerArguments
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