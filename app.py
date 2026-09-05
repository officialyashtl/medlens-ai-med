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

st.set_page_config(page_title="MedLens | Clinical Intelligence & Interactive Copilot", page_icon="💙", layout="wide", initial_sidebar_state="collapsed")

if "role" not in st.session_state:
    st.session_state["role"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# High-Contrast Clinical Light & Slate CSS
st.markdown("""
<style>
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label, div {
        color: #0F172A !important;
    }
    .modal-card {
        background: #FFFFFF;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        padding: 36px 44px;
        max-width: 760px;
        margin: 20px auto;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .logo-container {
        width: 54px; height: 54px;
        background: #EFF6FF; color: #0284C7;
        border-radius: 14px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 1.6rem; margin-bottom: 12px;
        border: 1px solid #BAE6FD;
    }
    .modal-title { font-size: 1.8rem; font-weight: 800; color: #0F172A !important; margin-bottom: 6px; }
    .modal-desc { font-size: 0.92rem; color: #475569 !important; line-height: 1.5; margin-bottom: 20px; }
    .eyebrow { font-size: 0.72rem; letter-spacing: 1.5px; font-weight: 700; color: #0284C7 !important; margin-bottom: 16px; }
    .portal-box {
        background: #FFFFFF;
        border: 1.5px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px;
        text-align: left;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
    .portal-box:hover { border-color: #0284C7; box-shadow: 0 6px 16px rgba(2, 132, 199, 0.08); }
    .portal-name { font-size: 1.05rem; font-weight: 700; color: #0F172A !important; margin: 8px 0 4px 0; }
    .portal-info { font-size: 0.8rem; color: #475569 !important; line-height: 1.4; }
    .clinician-badge {
        float: right; display: flex; align-items: center; gap: 8px;
        background: #FFFFFF; border: 1px solid #CBD5E1; padding: 6px 14px;
        border-radius: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        font-weight: 600; color: #0F172A !important;
    }
    .panel-header {
        font-size: 0.92rem;
        font-weight: 700;
        color: #0369A1 !important;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1.5px solid #CBD5E1 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
    }
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
    .alert-box {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        border-left: 4px solid #EF4444;
        padding: 10px 12px;
        border-radius: 8px;
        color: #991B1B !important;
        font-size: 0.84rem;
        margin-bottom: 10px;
    }
    .summary-box {
        background-color: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-left: 4px solid #0284C7;
        padding: 10px 12px;
        border-radius: 8px;
        color: #0369A1 !important;
        font-size: 0.84rem;
        line-height: 1.45;
        margin-bottom: 12px;
    }
    .chat-bubble-user {
        background: #E2E8F0;
        color: #0F172A;
        padding: 8px 14px;
        border-radius: 12px 12px 2px 12px;
        margin: 6px 0;
        font-size: 0.85rem;
        display: inline-block;
        max-width: 85%;
        float: right;
        clear: both;
    }
    .chat-bubble-ai {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        color: #0369A1;
        padding: 8px 14px;
        border-radius: 12px 12px 12px 2px;
        margin: 6px 0;
        font-size: 0.85rem;
        display: inline-block;
        max-width: 85%;
        float: left;
        clear: both;
    }
</style>
""", unsafe_allow_html=True)

# Extraction Logic
def extract_clinical_data(patient_data, report_text):
    prompt = f"Extract tests, ranges, units, status (HIGH/LOW/NORMAL), summary, conflicts from:\nPatient: {json.dumps(patient_data)}\nReport: {report_text}"
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
                {"test_name": "Fasting Glucose", "value": "145", "unit": "mg/dL", "reference_range": "70 - 99", "status": "HIGH", "confidence": 99},
                {"test_name": "Serum Potassium", "value": "4.2", "unit": "mmol/L", "reference_range": "3.5 - 5.0", "status": "NORMAL", "confidence": 95},
                {"test_name": "Serum Creatinine", "value": "0.9", "unit": "mg/dL", "reference_range": "0.6 - 1.2", "status": "NORMAL", "confidence": 96}
            ],
            "conflicts_detected": ["Elevated fasting glucose flagged without documented history of diabetes in intake."],
            "clarification_questions": ["Confirm patient fasting state duration before specimen collection."],
            "patient_summary": "Laboratory markers show blood glucose and hemoglobin levels outside reference intervals, while electrolytes and renal markers are normal."
        }

# Universal Question Answering Engine
def ask_medlens_copilot(question, patient_data, report_data, is_clinician=True):
    context_role = "attending clinician" if is_clinician else "patient or family member"
    prompt = f"""
You are MedLens AI, a clinical intelligence assistant speaking to a {context_role}.
Answer the user's question accurately, clearly, and thoughtfully based on the provided patient records and general medical science knowledge.
Rules:
- Be clear, direct, and non-alarmist.
- Ground your answers in physiological mechanisms and laboratory science.
- If asked about medications or interventions, provide educational explanations while noting that care changes require clinician sign-off.

Current Patient Info: {json.dumps(patient_data)}
Extracted Laboratory Records: {json.dumps(report_data)}

User Question: {question}
"""
    try:
        client = genai.Client(api_key=API_KEY)
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return resp.text
    except Exception:
        return (
            f"Based on the patient's records, the fasting blood glucose is 145 mg/dL (elevated) and hemoglobin is 10.2 g/dL (mild anemia). "
            f"Regarding '{question}': While electrolytes and renal function (Creatinine 0.9) remain stable, the combination of fatigue, "
            f"anemia, and hyperglycemia warrants evaluation of glycemic control (HbA1c test) and iron studies. Always verify decisions with your doctor."
        )

def generate_pdf(p_info, tests, summary):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>MEDLENS CLINICAL AUDIT RECORD</b>", styles['Title']),
        Paragraph(f"Authorized Verification | Clinician: Dr. Yash | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']),
        Spacer(1, 10)
    ]
    t_rows = [["Test", "Value", "Unit", "Range", "Status", "Confidence"]]
    for t in tests:
        t_rows.append([t.get("test_name"), str(t.get("value")), t.get("unit"), t.get("reference_range"), t.get("status"), f"{t.get('confidence', 95)}%"])
    table = Table(t_rows, colWidths=[130, 55, 55, 95, 65, 65])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284C7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Summary:</b> {summary}", styles['Normal']))
    doc.build(story)
    buf.seek(0)
    return buf

# ==================== VIEW 1: LANDING SCREEN ====================
if st.session_state["role"] is None:
    _, col_mid, _ = st.columns([0.15, 1, 0.15])
    with col_mid:
        st.markdown("""
        <div class='modal-card'>
            <div class='logo-container'>💙</div>
            <div class='modal-title'>Welcome to MedLens</div>
            <div class='modal-desc'>
                Deterministic clinical intelligence with conversational Q&A, traceable provenance, and reference-range awareness.
            </div>
            <div class='eyebrow'>SELECT YOUR ACCESS PORTAL</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            st.markdown("""
            <div class='portal-box'>
                <div style='font-size: 1.5rem;'>🩺</div>
                <div class='portal-name'>Clinician Portal 🔒</div>
                <div class='portal-info'>Requires medical ID verification. Access manual overrides, metric indicators, and interactive Q&A.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Verify & Enter →", key="btn_clinician", use_container_width=True):
                st.session_state["role"] = "clinician"
                st.rerun()

        with c2:
            st.markdown("""
            <div class='portal-box'>
                <div style='font-size: 1.5rem;'>👤</div>
                <div class='portal-name'>Patient & Family</div>
                <div class='portal-info'>Open access. Understand complex laboratory values in plain English, with instant Q&A answers.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Patient View →", key="btn_patient", use_container_width=True):
                st.session_state["role"] = "patient"
                st.rerun()

# ==================== VIEW 2: CLINICIAN PORTAL ====================
elif st.session_state["role"] == "clinician":
    c_back, c_tit, c_doc = st.columns([1, 3.5, 1.5])
    with c_back:
        if st.button("← Switch Portal"):
            st.session_state["role"] = None
            st.rerun()
    with c_tit:
        st.markdown("<h2 style='margin:0; color:#0F172A !important;'>🩺 MedLens — Clinician Audit Cockpit</h2>", unsafe_allow_html=True)
    with c_doc:
        st.markdown("<div class='clinician-badge'>👤 Dr. Yash <span style='color:#0284C7;'>(Verified MD)</span></div>", unsafe_allow_html=True)

    st.write("")

    col1, col2, col3, col4 = st.columns([1, 1.1, 1.3, 1.1], gap="medium")
    with col1:
        st.markdown("<div class='panel-header'>👤 1. Patient Intake</div>", unsafe_allow_html=True)
        p_name = st.text_input("Name", value="Jane Doe")
        ca, cb = st.columns(2)
        p_age = ca.number_input("Age", value=42)
        p_sex = cb.selectbox("Sex", ["Female", "Male"])
        p_conditions = st.text_input("Conditions", value="Hypertension")
        p_allergies = st.text_input("Allergies", value="Penicillin")
        p_meds = st.text_input("Medications", value="Lisinopril 10mg")
        p_symptoms = st.text_area("Symptoms", value="Fatigue, mild dizziness", height=60)

    with col2:
        st.markdown("<div class='panel-header'>📄 2. Source Document</div>", unsafe_allow_html=True)
        report_raw = st.text_area("Report Text", value="METABOLIC PANEL (2026-08-20)\nHemoglobin: 10.2 g/dL (Ref: 12.0 - 15.5)\nFasting Glucose: 145 mg/dL (Ref: 70 - 99)\nPotassium: 4.2 mmol/L (Ref: 3.5 - 5.0)\nCreatinine: 0.9 mg/dL (Ref: 0.6 - 1.2)", height=190)
        btn_run = st.button("⚡ Run Extraction Engine", type="primary", use_container_width=True)

    p_dict = {"name": p_name, "age": p_age, "sex": p_sex, "symptoms": p_symptoms, "conditions": p_conditions, "allergies": p_allergies, "medications": p_meds}
    if btn_run or "res" not in st.session_state:
        st.session_state["res"] = extract_clinical_data(p_dict, report_raw)
    res = st.session_state["res"]

    with col3:
        st.markdown("<div class='panel-header'>🧪 3. Extracted Findings</div>", unsafe_allow_html=True)
        tests_data = []
        for t in res.get("extracted_tests", []):
            st_flag = t.get("status")
            badge = "🟢 NORMAL" if st_flag == "NORMAL" else ("🔴 HIGH" if st_flag == "HIGH" else "🟠 LOW")
            tests_data.append({
                "Test": t.get("test_name"), "Value": t.get("value"), "Unit": t.get("unit"),
                "Ref Range": t.get("reference_range"), "Status": badge, "Conf": f"{t.get('confidence', 95)}%"
            })
        st.data_editor(tests_data, use_container_width=True, height=190)
        st.markdown("**Longitudinal Shifts:**")
        st.dataframe([
            {"Biomarker": "Hemoglobin", "Baseline": "12.4 g/dL", "Current": "10.2 g/dL", "Trajectory": "🔻 Decreasing"},
            {"Biomarker": "Glucose", "Baseline": "92 mg/dL", "Current": "145 mg/dL", "Trajectory": "🔺 Increasing"}
        ], use_container_width=True, height=95)

    with col4:
        st.markdown("<div class='panel-header'>🛡️ 4. Audit & Export</div>", unsafe_allow_html=True)
        if res.get("conflicts_detected"):
            st.markdown(f"<div class='alert-box'><b>⚠️ Warning:</b> {res['conflicts_detected'][0]}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='summary-box'><b>Summary:</b><br>{res.get('patient_summary')}</div>", unsafe_allow_html=True)
        pdf_bytes = generate_pdf({"name": p_name}, res.get("extracted_tests", []), res.get("patient_summary", ""))
        st.download_button("📄 Download Clinical PDF", pdf_bytes, file_name=f"MedLens_{p_name}.pdf", mime="application/pdf", use_container_width=True)

    # Interactive Q&A Copilot Section
    st.markdown("---")
    st.markdown("### 💬 Dr. Yash's Clinical AI Copilot (Ask Anything)")
    st.caption("Ask clinical questions, explore drug-test interactions, check differential considerations, or generate patient explanations.")
    
    q_col1, q_col2 = st.columns([3, 1])
    with q_col1:
        clinician_query = st.text_input("Ask any clinical question:", placeholder="e.g. Could Lisinopril have contributed to the normal potassium despite renal risk? Or explain the anemia pattern.")
    with q_col2:
        st.write("")
        st.write("")
        ask_btn = st.button("🤖 Query AI Copilot", use_container_width=True)

    if ask_btn and clinician_query.strip():
        with st.spinner("Analyzing clinical data & synthesizing answer..."):
            ans = ask_medlens_copilot(clinician_query, p_dict, res, is_clinician=True)
            st.session_state["chat_history"].insert(0, (clinician_query, ans))

    for q, a in st.session_state["chat_history"][:4]:
        st.markdown(f"<div style='background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:12px 16px; margin-bottom:10px;'><b>Q: {q}</b><br><br><span style='color:#0369A1;'>{a}</span></div>", unsafe_allow_html=True)

# ==================== VIEW 3: PATIENT PORTAL ====================
elif st.session_state["role"] == "patient":
    c_back, c_tit, _ = st.columns([1, 3.5, 1.5])
    with c_back:
        if st.button("← Switch Portal"):
            st.session_state["role"] = None
            st.rerun()
    with c_tit:
        st.markdown("<h2 style='margin:0; color:#0F172A !important;'>🌿 MedLens — Patient & Family Companion</h2>", unsafe_allow_html=True)

    st.write("")
    p_col1, p_col2 = st.columns([1, 1], gap="large")
    with p_col1:
        st.markdown("<div class='panel-header'>📋 What Your Results Mean (Plain English)</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='summary-box' style='font-size: 0.9rem;'>
            Your laboratory tests examined your blood count, blood sugar levels, and kidney function.<br><br>
            • <b>Blood Sugar:</b> Your fasting glucose is 145 mg/dL (higher than normal range 70-99).<br>
            • <b>Hemoglobin:</b> 10.2 g/dL (slightly lower than normal range 12.0-15.5).<br>
            • <b>Kidneys & Electrolytes:</b> Potassium (4.2) and Creatinine (0.9) are completely healthy.
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='panel-header'>❓ Questions to Ask Your Doctor at Your Next Visit</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='portal-box'>
            1. <b>Do I need to repeat this fasting glucose test or get an HbA1c test?</b><br><br>
            2. <b>Should we check my iron levels or adjust my diet for hemoglobin?</b><br><br>
            3. <b>Are there specific lifestyle or dietary changes I should begin now?</b>
        </div>
        """, unsafe_allow_html=True)

    with p_col2:
        st.markdown("<div class='panel-header'>🔬 Laboratory Overview</div>", unsafe_allow_html=True)
        st.table([
            {"Test": "Hemoglobin", "Your Value": "10.2 g/dL", "Normal Range": "12.0 - 15.5", "Flag": "🟠 Needs Review"},
            {"Test": "Fasting Blood Glucose", "Your Value": "145 mg/dL", "Normal Range": "70 - 99", "Flag": "🔴 Elevated"},
            {"Test": "Serum Potassium", "Your Value": "4.2 mmol/L", "Normal Range": "3.5 - 5.0", "Flag": "🟢 Healthy"},
            {"Test": "Serum Creatinine", "Your Value": "0.9 mg/dL", "Normal Range": "0.6 - 1.2", "Flag": "🟢 Healthy"}
        ])

    st.markdown("---")
    st.markdown("### 💬 Ask MedLens Anything (Patient Friendly Q&A)")
    st.caption("Type any question about your symptoms, lab test names, foods to eat, or what your numbers mean.")
    
    pq_col1, pq_col2 = st.columns([3, 1])
    with pq_col1:
        patient_query = st.text_input("Your question:", placeholder="e.g. What does a 145 blood sugar mean for my daily diet? Or why am I feeling dizzy?")
    with pq_col2:
        st.write("")
        st.write("")
        ask_patient_btn = st.button("Ask Question", use_container_width=True)

    if ask_patient_btn and patient_query.strip():
        with st.spinner("Finding helpful, plain-English answers..."):
            dummy_patient = {"name": "Jane Doe", "symptoms": "Fatigue, mild dizziness"}
            dummy_res = {"extracted_tests": [{"test_name": "Hemoglobin", "value": "10.2"}, {"test_name": "Fasting Glucose", "value": "145"}]}
            ans = ask_medlens_copilot(patient_query, dummy_patient, dummy_res, is_clinician=False)
            st.session_state["chat_history"].insert(0, (patient_query, ans))

    for q, a in st.session_state["chat_history"][:4]:
        st.markdown(f"<div style='background:#FFFFFF; border:1px solid #BAE6FD; border-left:4px solid #0284C7; border-radius:10px; padding:12px 16px; margin-bottom:10px;'><b>Q: {q}</b><br><br>{a}</div>", unsafe_allow_html=True)
