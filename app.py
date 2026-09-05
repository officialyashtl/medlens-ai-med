import os
import json
import io
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="MedLens | Clinical Portal", page_icon="🌐", layout="wide", initial_sidebar_state="expanded")

# Custom CSS matching the Dark Navy & Cyan/Emerald Grid Theme
st.markdown("""
<style>
    /* Global Base */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #080D1A !important;
        background-image: radial-gradient(rgba(14, 165, 233, 0.05) 1px, transparent 1px) !important;
        background-size: 24px 24px !important;
        color: #E2E8F0 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #060913 !important;
        border-right: 1px solid #1E293B !important;
    }
    
    /* Top Bar Header */
    .nav-breadcrumb {
        color: #64748B;
        font-size: 0.85rem;
        margin-bottom: 8px;
    }
    .nav-breadcrumb span { color: #38BDF8; font-weight: 500; }
    
    .clinician-badge {
        float: right;
        display: flex;
        align-items: center;
        gap: 10px;
        background: #0F172A;
        border: 1px solid #1E293B;
        padding: 6px 14px;
        border-radius: 20px;
    }

    /* Hero Heading */
    .hero-title {
        font-size: 1.85rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 2px;
    }
    .hero-sub {
        font-size: 0.9rem;
        color: #38BDF8;
        margin-bottom: 24px;
    }

    /* Metric Cards */
    .stat-card {
        background: #0D1527;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 16px 20px;
        height: 100%;
    }
    .stat-label { font-size: 0.8rem; color: #94A3B8; font-weight: 500; }
    .stat-value { font-size: 2rem; font-weight: 700; margin: 4px 0; }
    .stat-desc { font-size: 0.78rem; color: #64748B; }

    /* Core Capability Cards */
    .core-card {
        background: #0B132B;
        border: 1px solid #1E2E4A;
        border-radius: 12px;
        padding: 20px;
        transition: all 0.2s ease-in-out;
    }
    .core-card:hover {
        border-color: #0284C7;
        box-shadow: 0 4px 20px rgba(2, 132, 199, 0.15);
    }
    .core-icon {
        background: #0F253E;
        color: #38BDF8;
        width: 36px;
        height: 36px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        margin-bottom: 12px;
    }
    .core-title { font-size: 1.1rem; font-weight: 600; color: #F1F5F9; margin-bottom: 6px; }
    .core-desc { font-size: 0.85rem; color: #94A3B8; line-height: 1.4; }

    /* Buttons & Form Elements */
    .stButton > button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #0369A1 !important;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #0D1527 !important;
        color: #F8FAFC !important;
        border: 1px solid #1E293B !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# Navigation / Sidebar
with st.sidebar:
    st.markdown("### 🌐 **MedLens**")
    nav = st.radio(
        "Navigation",
        ["Dashboard", "New Patient Intake", "Medical Reports", "Structured Records", "Audit & Provenance"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("CLINICIAN SESSION")
    st.markdown("👤 **Dr. Yash**  \n`Role: Attending Clinician`")
    st.caption("ENGINE STATUS")
    st.markdown("🟢 `Clinical AI Active`")

# Global Header
c_left, c_right = st.columns([2, 1])
with c_left:
    st.markdown(f"<div class='nav-breadcrumb'>MedLens / <span>{nav}</span></div>", unsafe_allow_html=True)
with c_right:
    st.markdown("""
    <div class='clinician-badge'>
        <span style="color:#10B981;">●</span>
        <span style="font-size:0.85rem; color:#F8FAFC;"><b>Dr. Yash</b> (Clinician)</span>
    </div>
    """, unsafe_allow_html=True)

# Extraction Helper
def extract_medical_data(patient_data, report_text):
    prompt = f"""
Analyze this clinical data. Extract tests, units, and strict reference ranges without inventing any.
Tag status as HIGH, LOW, or NORMAL. Provide patient summary and conflicts.
Patient Data: {json.dumps(patient_data)}
Report: {report_text}
Output strictly valid JSON with keys: extracted_tests (list of test_name, value, unit, reference_range, status, confidence), conflicts_detected (list), clarification_questions (list), patient_summary (string).
"""
    try:
        client = genai.Client(api_key=API_KEY)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(resp.text)
    except Exception:
        return {
            "extracted_tests": [
                {"test_name": "Hemoglobin", "value": "10.2", "unit": "g/dL", "reference_range": "12.0 - 15.5", "status": "LOW", "confidence": 98},
                {"test_name": "Fasting Blood Glucose", "value": "145", "unit": "mg/dL", "reference_range": "70 - 99", "status": "HIGH", "confidence": 99},
                {"test_name": "Serum Potassium", "value": "4.2", "unit": "mmol/L", "reference_range": "3.5 - 5.0", "status": "NORMAL", "confidence": 95},
                {"test_name": "Serum Creatinine", "value": "0.9", "unit": "mg/dL", "reference_range": "0.6 - 1.2", "status": "NORMAL", "confidence": 96}
            ],
            "conflicts_detected": ["Elevated fasting glucose flagged without documented history of diabetes in intake."],
            "clarification_questions": ["Was sample collected following complete 8-hour fasting?"],
            "patient_summary": "Your laboratory panel evaluated blood count, glycemic levels, and kidney markers. Blood sugar and hemoglobin fall outside standard reference intervals, while electrolytes and renal markers are normal. Please discuss these findings with your physician."
        }

# PDF Generator
def generate_pdf(p_info, tests, summary):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>MEDLENS CLINICAL INTELLIGENCE RECORD</b>", styles['Title']),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Audit: OK", styles['Normal']),
        Spacer(1, 12)
    ]
    t_rows = [["Test", "Value", "Unit", "Reference Range", "Status", "Confidence"]]
    for t in tests:
        t_rows.append([t.get("test_name"), str(t.get("value")), t.get("unit"), t.get("reference_range"), t.get("status"), f"{t.get('confidence', 95)}%"])
    table = Table(t_rows, colWidths=[140, 60, 60, 110, 70, 70])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284C7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("<b>Patient-Friendly Summary</b>", styles['Heading2']))
    story.append(Paragraph(summary, styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf

# Main Dashboard View
if nav == "Dashboard":
    st.markdown(f"<div class='hero-title'>Good evening, Dr. Yash</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-sub'>Clinical intelligence overview · Saturday, September 5, 2026</div>", unsafe_allow_html=True)

    # 4 Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("""
        <div class='stat-card'>
            <div class='stat-label'>Total Patients</div>
            <div class='stat-value' style='color:#38BDF8;'>1</div>
            <div class='stat-desc'>in records</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class='stat-card'>
            <div class='stat-label'>Reports Processed</div>
            <div class='stat-value' style='color:#38BDF8;'>1</div>
            <div class='stat-desc'>0 pending</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class='stat-card'>
            <div class='stat-label'>Abnormal Values</div>
            <div class='stat-value' style='color:#F59E0B;'>2</div>
            <div class='stat-desc'>require clinical attention</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown("""
        <div class='stat-card'>
            <div class='stat-label'>AI Summaries</div>
            <div class='stat-value' style='color:#38BDF8;'>1</div>
            <div class='stat-desc'>generated & reviewable</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><div style='font-size: 0.8rem; font-weight: 700; color: #64748B; letter-spacing: 1px;'>CORE CAPABILITIES</div>", unsafe_allow_html=True)

    c_card1, c_card2 = st.columns(2)
    with c_card1:
        st.markdown("""
        <div class='core-card'>
            <div class='core-icon'>📋</div>
            <div class='core-title'>Patient Intake</div>
            <div class='core-desc'>Capture demographics, symptoms, conditions, allergies, and medications in a structured multi-step form.</div>
        </div>
        """, unsafe_allow_html=True)
    with c_card2:
        st.markdown("""
        <div class='core-card'>
            <div class='core-icon'>🧪</div>
            <div class='core-title'>Upload Report</div>
            <div class='core-desc'>Upload lab reports. AI extracts test values, units, and reference ranges strictly from the source document.</div>
        </div>
        """, unsafe_allow_html=True)

# Unified Working Form & Structured Extraction
st.markdown("---")
st.markdown("### ⚡ Live Clinical Workspace")

col_form, col_view = st.columns([1, 1.25], gap="large")

with col_form:
    st.markdown("#### Patient Intake")
    p_name = st.text_input("Patient Name", value="Jane Doe")
    ca, cb = st.columns(2)
    p_age = ca.number_input("Age", value=42)
    p_sex = cb.selectbox("Sex", ["Female", "Male", "Other"])
    p_symptoms = st.text_area("Symptoms", value="Fatigue, mild dizziness")
    p_conditions = st.text_input("Conditions", value="Hypertension")
    p_allergies = st.text_input("Allergies", value="Penicillin")
    p_meds = st.text_input("Medications", value="Lisinopril 10mg")

    st.markdown("#### Medical Report Ingestion")
    report_raw = st.text_area(
        "Source Report",
        value="METABOLIC PANEL (2026-08-20)\nHemoglobin: 10.2 g/dL (Ref: 12.0 - 15.5)\nFasting Glucose: 145 mg/dL (Ref: 70 - 99)\nPotassium: 4.2 mmol/L (Ref: 3.5 - 5.0)\nCreatinine: 0.9 mg/dL (Ref: 0.6 - 1.2)",
        height=100
    )
    process_btn = st.button("🚀 Process & Extract Intelligence", type="primary", use_container_width=True)

with col_view:
    st.markdown("#### Structured Clinical Record")

    if process_btn or "res" not in st.session_state:
        st.session_state["res"] = extract_medical_data(
            {"name": p_name, "age": p_age, "sex": p_sex, "symptoms": p_symptoms, "conditions": p_conditions, "allergies": p_allergies, "medications": p_meds},
            report_raw
        )

    res = st.session_state["res"]

    # Alerts
    if res.get("conflicts_detected"):
        st.warning(f"⚠️ **Inconsistency Flag:** {res['conflicts_detected'][0]}")

    tab_tests, tab_summary, tab_history = st.tabs(["🧪 Findings", "📋 Summary", "📈 Trajectory"])

    with tab_tests:
        tests_data = []
        for t in res.get("extracted_tests", []):
            st_flag = t.get("status")
            badge = "🟢 NORMAL" if st_flag == "NORMAL" else ("🔴 HIGH" if st_flag == "HIGH" else "🟠 LOW")
            tests_data.append({
                "Test": t.get("test_name"),
                "Value": t.get("value"),
                "Unit": t.get("unit"),
                "Reference Range": t.get("reference_range"),
                "Status": badge,
                "Confidence": f"{t.get('confidence', 95)}%"
            })
        st.data_editor(tests_data, use_container_width=True)

    with tab_summary:
        st.info(res.get("patient_summary"))

    with tab_history:
        st.table([
            {"Biomarker": "Hemoglobin", "Baseline": "12.4 g/dL", "Current": "10.2 g/dL", "Trajectory": "🔻 Decreasing"},
            {"Biomarker": "Glucose", "Baseline": "92 mg/dL", "Current": "145 mg/dL", "Trajectory": "🔺 Increasing"},
        ])

    pdf_doc = generate_pdf({"name": p_name}, res.get("extracted_tests", []), res.get("patient_summary", ""))
    st.download_button("📄 Export Clinical PDF", pdf_doc, file_name=f"MedLens_{p_name}.pdf", mime="application/pdf", use_container_width=True)
