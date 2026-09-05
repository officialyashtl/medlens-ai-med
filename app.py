import os
import json
import streamlit as st
from dotenv import load_dotenv
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="MedLens | Clinical Intelligence", layout="wide", page_icon="🩺")

st.title("🩺 MedLens — Clinical Information Intelligence")
st.warning(
    "⚠️ **Responsible AI Disclaimer:** MedLens is an information organization tool, "
    "not a clinical diagnostic device. It does not provide medical diagnoses, treatment advice, "
    "or prescription adjustments. Consult a licensed healthcare professional for medical decisions."
)

client = None
if api_key:
    client = genai.Client(api_key=api_key)

def analyze_medical_data(patient_data, report_text):
    prompt = f"""
You are an expert clinical data parsing system following strict Responsible AI guidelines.
Analyze the provided Patient Information and Raw Medical Report text.

CRITICAL INSTRUCTIONS:
1. Extract all laboratory tests, their values, units, and the exact reference ranges given in the report text.
2. Determine 'status' strictly as 'LOW', 'NORMAL', or 'HIGH' based ONLY on the reference ranges in the report. If no reference range is provided, set status to 'UNKNOWN'. DO NOT invent reference ranges.
3. Identify conflicts or inconsistencies (e.g., patient claims allergy to penicillin but amoxicillin is prescribed, or mismatched test results).
4. Formulate 1-3 targeted, context-aware clarification questions for a clinician or patient.
5. Create a concise, empathetic, patient-friendly summary (explain what tests were run without diagnosing any conditions).
6. Calculate an extraction confidence score between 0 and 100%.

Patient Data:
{json.dumps(patient_data, indent=2)}

Medical Report Text:
{report_text}

Respond ONLY with a valid, clean JSON object with this exact schema:
{{
  "extracted_tests": [
    {{"test_name": "...", "value": "...", "unit": "...", "reference_range": "...", "status": "LOW|NORMAL|HIGH|UNKNOWN", "confidence": 95}}
  ],
  "observations": ["observation 1", "observation 2"],
  "conflicts_detected": ["conflict 1 if any"],
  "clarification_questions": ["question 1"],
  "patient_summary": "Plain English summary here..."
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

def create_pdf(patient_info, structured_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>MedLens Clinical Summary Record</b>", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<i>Source Provenance: AI-Extracted & Clinician-Reviewable</i>", styles['Italic']))
    elements.append(Spacer(1, 15))

    p_data = [
        ["Patient Name", patient_info.get("name", "N/A"), "Age / Sex", f"{patient_info.get('age', '')} / {patient_info.get('sex', '')}"],
        ["Allergies", patient_info.get("allergies", "None"), "Conditions", patient_info.get("conditions", "None")],
        ["Current Meds", patient_info.get("medications", "None"), "Symptoms", patient_info.get("symptoms", "None")]
    ]
    t_patient = Table(p_data, colWidths=[100, 170, 100, 170])
    t_patient.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(t_patient)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Structured Lab Findings</b>", styles['Heading2']))
    test_rows = [["Test", "Value", "Unit", "Reference Range", "Status", "Source"]]
    for t in structured_data.get("extracted_tests", []):
        test_rows.append([t.get("test_name"), t.get("value"), t.get("unit"), t.get("reference_range"), t.get("status"), "Report (AI Extracted)"])
    
    t_tests = Table(test_rows, colWidths=[140, 70, 70, 110, 70, 80])
    t_tests.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_tests)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("<b>Patient-Friendly Summary</b>", styles['Heading2']))
    elements.append(Paragraph(structured_data.get("patient_summary", "N/A"), styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("1. Patient Information Intake")
    st.caption("🏷️ Source Provenance: **User Provided**")
    
    name = st.text_input("Full Name", value="Jane Doe")
    c1, c2 = st.columns(2)
    age = c1.number_input("Age", min_value=0, max_value=120, value=42)
    sex = c2.selectbox("Biological Sex", ["Female", "Male", "Other"])
    symptoms = st.text_area("Reported Symptoms", value="Persistent fatigue, dry cough, dizziness for 2 weeks")
    conditions = st.text_input("Pre-existing Conditions", value="Hypertension, Seasonal Allergies")
    allergies = st.text_input("Known Allergies", value="Penicillin")
    medications = st.text_input("Current Medications", value="Lisinopril 10mg daily, Multivitamin")

    st.markdown("---")
    st.subheader("2. Medical Report Ingestion")
    uploaded_file = st.file_uploader("Upload Medical Report (PDF or TXT)", type=["pdf", "txt"])
    
    sample_report = (
        "COMPREHENSIVE METABOLIC & HEMATOLOGY PANEL\n"
        "Collection Date: 2026-08-20\n"
        "Hemoglobin: 10.2 g/dL (Reference Range: 12.0 - 15.5 g/dL)\n"
        "Fasting Blood Glucose: 145 mg/dL (Reference Range: 70 - 99 mg/dL)\n"
        "Potassium: 4.2 mmol/L (Reference Range: 3.5 - 5.0 mmol/L)\n"
        "Serum Creatinine: 0.9 mg/dL (Reference Range: 0.6 - 1.2 mg/dL)\n"
        "WBC Count: 7.8 10*3/uL (Reference Range: 4.5 - 11.0 10*3/uL)\n"
        "Notes: Mild microcytic anemia observed on smear."
    )
    report_text = st.text_area("Or Paste Raw Medical Report Text", value=sample_report, height=180)

    if uploaded_file is not None:
        if uploaded_file.name.endswith(".pdf"):
            reader = PyPDF2.PdfReader(uploaded_file)
            report_text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        else:
            report_text = uploaded_file.read().decode("utf-8")
        st.success("File content loaded successfully!")

    process_btn = st.button("🚀 Process & Structure Records", type="primary", use_container_width=True)

with col_right:
    st.subheader("3. Structured Medical Record & Clinical Intelligence")

    if process_btn:
        if not client:
            st.error("Please configure GEMINI_API_KEY in your environment or .env file.")
        else:
            patient_payload = {
                "name": name, "age": age, "sex": sex,
                "symptoms": symptoms, "conditions": conditions,
                "allergies": allergies, "medications": medications
            }
            with st.spinner("Analyzing document, matching reference ranges, and checking conflicts..."):
                try:
                    result = analyze_medical_data(patient_payload, report_text)
                    st.session_state["result"] = result
                    st.session_state["patient_payload"] = patient_payload
                except Exception as e:
                    st.error(f"Processing error: {str(e)}")

    if "result" in st.session_state:
        res = st.session_state["result"]
        p_info = st.session_state["patient_payload"]

        conflicts = res.get("conflicts_detected", [])
        if conflicts and len(conflicts) > 0 and conflicts[0] != "":
            st.error("⚠️ **Inconsistency / Conflict Detected:**")
            for c in conflicts:
                st.write(f"- {c}")

        st.markdown("#### 🧪 Structured Lab Findings")
        st.caption("🏷️ Source Provenance: **AI Extracted from Medical Report**")
        
        tests = res.get("extracted_tests", [])
        if tests:
            formatted_data = []
            for t in tests:
                status = t.get("status", "UNKNOWN").upper()
                badge = "🟢 NORMAL" if status == "NORMAL" else ("🔴 HIGH" if status == "HIGH" else ("🟠 LOW" if status == "LOW" else "⚪ UNKNOWN"))
                formatted_data.append({
                    "Test Name": t.get("test_name"),
                    "Value": t.get("value"),
                    "Unit": t.get("unit"),
                    "Reference Range": t.get("reference_range"),
                    "Status": badge,
                    "Confidence": f"{t.get('confidence', 95)}%"
                })
            
            edited_df = st.data_editor(formatted_data, use_container_width=True, num_rows="dynamic")
        
        clarifications = res.get("clarification_questions", [])
        if clarifications:
            with st.expander("❓ Context-Aware Clarification Questions for Clinician", expanded=True):
                for q in clarifications:
                    st.write(f"• {q}")

        st.markdown("#### 📋 Patient-Friendly Summary")
        st.info(res.get("patient_summary", "No summary available."))

        pdf_bytes = create_pdf(p_info, res)
        st.download_button(
            label="📥 Download Verified Clinical Record (PDF)",
            data=pdf_bytes,
            file_name=f"MedLens_Record_{name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
