import { useEffect, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [doctors, setDoctors] = useState([]);
  const [doctorId, setDoctorId] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [patientName, setPatientName] = useState("");

  const [appointmentId, setAppointmentId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [available, setAvailable] = useState(null);

  // Voice
  const [listening, setListening] = useState(false);

  // ============================================================
  // LOAD DOCTORS
  // ============================================================
  useEffect(() => {
    fetch(`${API}/doctors/`)
      .then((response) => response.json())
      .then((data) => setDoctors(data))
      .catch(() => {
        setError("Unable to load doctors.");
      });
  }, []);

  // ============================================================
  // CLEAR MESSAGES
  // ============================================================
  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  // ============================================================
  // CHECK AVAILABILITY
  // ============================================================
  const checkAvailability = async () => {
    clearMessages();

    if (!doctorId || !date || !time) {
      setError("Please select doctor, date and time.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API}/availability/?doctor_id=${doctorId}&date=${date}&time=${time}`
      );

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Could not check availability.");
        return;
      }

      setAvailable(data.available);

      if (data.available) {
        setMessage("The selected time is available.");
      } else {
        setError("The selected time is not available.");
      }
    } catch (err) {
      setError("Backend server is not reachable.");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // BOOK APPOINTMENT
  // ============================================================
  const bookAppointment = async () => {
    clearMessages();

    if (!patientName || !doctorId || !date || !time) {
      setError("Please fill all appointment details.");
      return;
    }

    try {
      setLoading(true);

      const url =
        `${API}/appointments/book` +
        `?patient_name=${encodeURIComponent(patientName)}` +
        `&doctor_id=${doctorId}` +
        `&date=${date}` +
        `&time=${encodeURIComponent(time)}`;

      const response = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Unable to book appointment.");
        return;
      }

      setAppointmentId(data.appointment_id);

      setMessage(
        `Appointment booked successfully! Appointment ID: ${data.appointment_id}`
      );

      setAvailable(true);

      speak(
        `Your appointment with ${data.doctor} has been booked successfully at ${data.time}.`
      );
    } catch (err) {
      setError("Backend server is not reachable.");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // CANCEL APPOINTMENT
  // ============================================================
  const cancelAppointment = async () => {
    clearMessages();

    if (!appointmentId) {
      setError("Please enter or select an appointment ID.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API}/appointments/${appointmentId}/cancel`,
        {
          method: "PUT",
          headers: {
            Accept: "application/json",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Unable to cancel appointment.");
        return;
      }

      setMessage(data.message);

      speak("Your appointment has been cancelled successfully.");
    } catch (err) {
      setError("Backend server is not reachable.");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // RESCHEDULE APPOINTMENT
  // ============================================================
  const rescheduleAppointment = async () => {
    clearMessages();

    if (!appointmentId || !date || !time) {
      setError("Appointment ID, date and time are required.");
      return;
    }

    try {
      setLoading(true);

      const url =
        `${API}/appointments/${appointmentId}/reschedule` +
        `?new_date=${date}` +
        `&new_time=${encodeURIComponent(time)}`;

      const response = await fetch(url, {
        method: "PUT",
        headers: {
          Accept: "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || "Unable to reschedule appointment.");
        return;
      }

      setMessage(data.message);

      speak(
        `Your appointment has been rescheduled to ${data.new_date} at ${data.new_time}.`
      );
    } catch (err) {
      setError("Backend server is not reachable.");
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // TEXT TO SPEECH
  // ============================================================
  const speak = (text) => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1;

      window.speechSynthesis.speak(utterance);
    }
  };

  // ============================================================
  // OPEN PIPECAT VOICE ASSISTANT
  // ============================================================
  const startListening = () => {
    setListening(true);
    setError("");
    setMessage("");

    window.open(
      "http://localhost:7860/client/",
      "_blank",
      "noopener,noreferrer"
    );

    // Reset button state after opening Pipecat
    setTimeout(() => {
      setListening(false);
    }, 1000);
  };

  // ============================================================
  // UI
  // ============================================================
  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Medical Voice Assistant</h1>
          <p>Your smart appointment assistant</p>
        </div>

        <button
          className={`voice-button ${listening ? "listening" : ""}`}
          onClick={startListening}
        >
          🎤 {listening ? "Opening AI..." : "Speak"}
        </button>
      </header>

      <main className="container">
        {/* HERO */}
        <section className="hero">
          <div>
            <span className="badge">AI Medical Assistant</span>

            <h2>
              Book your doctor
              <br />
              appointment easily.
            </h2>

            <p>
              Select a doctor, check availability and manage your appointment
              from one place.
            </p>
          </div>

          <div className="hero-icon">🩺</div>
        </section>

        {/* BOOK APPOINTMENT */}
        <section className="card">
          <h2>Book an Appointment</h2>

          <p className="subtitle">
            Enter your details and choose your preferred time.
          </p>

          <div className="form-grid">
            <div className="field full">
              <label>Patient Name</label>

              <input
                type="text"
                placeholder="Enter patient name"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
              />
            </div>

            <div className="field">
              <label>Doctor</label>

              <select
                value={doctorId}
                onChange={(e) => {
                  setDoctorId(e.target.value);
                  setAvailable(null);
                }}
              >
                <option value="">Select doctor</option>

                {doctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    {doctor.name} - {doctor.specialty}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Date</label>

              <input
                type="date"
                value={date}
                onChange={(e) => {
                  setDate(e.target.value);
                  setAvailable(null);
                }}
              />
            </div>

            <div className="field">
              <label>Time</label>

              <input
                type="time"
                value={time}
                onChange={(e) => {
                  setTime(e.target.value);
                  setAvailable(null);
                }}
              />
            </div>
          </div>

          <div className="buttons">
            <button
              className="secondary-button"
              onClick={checkAvailability}
              disabled={loading}
            >
              Check Availability
            </button>

            <button
              className="primary-button"
              onClick={bookAppointment}
              disabled={loading}
            >
              Book Appointment
            </button>
          </div>

          {available === true && (
            <div className="success-box">
              ✓ This appointment time is available.
            </div>
          )}

          {available === false && (
            <div className="error-box">
              ✕ This appointment time is not available.
            </div>
          )}
        </section>

        {/* MANAGE APPOINTMENT */}
        <section className="card management-card">
          <h2>Manage Appointment</h2>

          <p className="subtitle">
            Cancel or reschedule an existing appointment.
          </p>

          <div className="field">
            <label>Appointment ID</label>

            <input
              type="number"
              placeholder="Enter appointment ID"
              value={appointmentId}
              onChange={(e) => setAppointmentId(e.target.value)}
            />
          </div>

          <div className="buttons">
            <button
              className="danger-button"
              onClick={cancelAppointment}
              disabled={loading}
            >
              Cancel Appointment
            </button>

            <button
              className="secondary-button"
              onClick={rescheduleAppointment}
              disabled={loading}
            >
              Reschedule
            </button>
          </div>
        </section>

        {/* MESSAGES */}
        {message && (
          <div className="message success-box">
            ✓ {message}
          </div>
        )}

        {error && (
          <div className="message error-box">
            ⚠ {error}
          </div>
        )}
      </main>

      <footer>
        <p>Medical Voice Assistant © 2026</p>
      </footer>
    </div>
  );
}

export default App;