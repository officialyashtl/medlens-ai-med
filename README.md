# MedLens — AI-Powered Clinical Information Intelligence

MedLens transforms fragmented medical records, patient intakes, and diagnostic reports into an organized, traceable, and reviewable clinical cockpit.

#### Key Architectural Highlights:
1. **Intake & Multi-Modal Ingestion:** Captures structured patient profiles (demographics, medications, allergies, symptoms) and parses laboratory PDF/text reports.
2. **Reference-Range Intelligence & Provenance:** Automatically benchmarks values strictly against report-defined reference intervals (HIGH/LOW/NORMAL) with transparent data provenance indicators.
3. **Clinical Safety & Conflict Detection:** Flags discrepancies between intake conditions and laboratory abnormalities (e.g., undocumented hyperglycemia).
4. **Human-in-the-Loop Verification:** Clinicians can interactively edit, modify, and verify extracted values directly in the data grid.
5. **Longitudinal Trajectory Tracking:** Compares current biomarker levels against previous patient baselines to visualize clinical progression.
6. **Executive PDF Audit Export:** Generates verifiable, timestamped clinical PDF summaries complete with audit IDs and clinician sign-offs.
7. **Strict Responsible AI Compliance:** Designed solely for synthesis and organization; adheres to non-diagnostic standards with zero prescription or dosage hallucination.

---

### Tech Stack
- **Framework:** Python, Streamlit
- **Intelligence Engine:** Google Gemini 2.5 Flash (`google-genai`)
- **Document Ingestion:** PyPDF2
- **Clinical PDF Generation:** ReportLab
- **Configuration:** Python Dotenv

---

### Quickstart

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/officialyashtl/medlens-ai-med.git
   cd medlens-ai-med
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY="your_api_key_here"
   ```

4. **Run the Clinical Portal:**
   ```bash
   streamlit run app.py
   ```
