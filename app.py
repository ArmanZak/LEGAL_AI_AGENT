import os
import json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClearClause",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

div[data-testid="stButton"] button[kind="primary"] {
    background-color: #1a1a2e;
    color: white;
    border-radius: 8px;
    font-size: 16px;
    padding: 0.6rem;
}

button[data-baseweb="tab"] {
    font-size: 15px;
    font-weight: 500;
}

div[data-testid="stCode"] {
    border-left: 3px solid #2ecc71;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)

# ─── Session State ───────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state["result"] = None
if "last_clause" not in st.session_state:
    st.session_state["last_clause"] = ""

# ─── Groq Helpers ────────────────────────────────────────────────────────────────
def get_groq_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key or api_key == "your_groq_api_key_here":
        st.error("GROQ_API_KEY not found. Add it to .env locally or Streamlit Secrets on cloud.")
        st.stop()

    return Groq(api_key=api_key)


def build_system_prompt():
    return """You are ClearClause, an expert legal document analyst with 20 years of experience in contract law across employment, real estate, intellectual property, and commercial agreements.

Your job is to analyze contract clauses and return structured JSON. You never give legal advice — you explain and flag risks.

CRITICAL OUTPUT RULES:
1. Return ONLY valid JSON. No preamble, no explanation, no markdown fences.
2. Never say "I cannot" or "consult a lawyer" inside the JSON fields — the disclaimer is shown in the UI already.
3. Be specific. Generic responses like "this clause may be risky" are not acceptable.
4. Suggested language in negotiation_tips must be actual counter-clause text, not generic advice.
5. Severity must be exactly "HIGH", "MEDIUM", or "LOW" in uppercase.
6. overall_risk must be exactly "HIGH", "MEDIUM", or "LOW" in uppercase.

OUTPUT SCHEMA (return exactly this structure):
{
  "plain_english": "string — 2 to 4 sentences explaining what this clause means in plain language. What does it require, permit, or forbid? Who benefits from it?",
  "clause_type": "string — detected clause type e.g. Non-compete, Indemnification, Termination, Arbitration, IP Assignment, Limitation of Liability, etc.",
  "overall_risk": "HIGH | MEDIUM | LOW",
  "red_flags": [
    {
      "issue": "string — short title of the problem (max 10 words)",
      "severity": "HIGH | MEDIUM | LOW",
      "explanation": "string — 1 to 2 sentences explaining exactly why this is a problem and who it harms"
    }
  ],
  "negotiation_tips": [
    {
      "point": "string — what to ask for or change (max 15 words)",
      "suggested_language": "string — exact counter-clause text the user can propose, written in legal style"
    }
  ]
}

If there are no red flags, return an empty array [].
If there are no negotiation tips needed, return an empty array [].
Maximum 4 red flags. Maximum 3 negotiation tips. Quality over quantity."""


def build_user_prompt(clause_text, contract_type, perspective):
    return f"""Analyze the following contract clause.

Contract type: {contract_type}
Explain as if the reader is: {perspective}

CLAUSE TO ANALYZE:
\"\"\"
{clause_text}
\"\"\"

Return your analysis as JSON following the exact schema provided."""


def analyze_clause(clause_text, contract_type, perspective):
    client = get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(clause_text, contract_type, perspective)}
        ],
        temperature=0.2,
        max_tokens=1500
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        st.error("Could not parse the model response as JSON.")
        st.text("Raw model output:")
        st.code(raw)
        st.stop()


# ─── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ ClearClause")
    st.divider()

    contract_type = st.selectbox(
        "Contract type",
        options=[
            "General / Unknown",
            "Employment Agreement",
            "NDA / Confidentiality",
            "Rental / Lease",
            "Freelance / Service Agreement",
            "SaaS / Software License",
            "Partnership Agreement",
        ]
    )

    perspective = st.radio(
        "Explain as if I am a",
        options=[
            "Complete layperson (no legal background)",
            "Small business owner",
            "Software developer / freelancer",
        ]
    )

    st.divider()

    st.info(
        "**How it works**\n\n"
        "1. Paste your clause\n"
        "2. Select contract type\n"
        "3. Get plain English + red flags + negotiation tips"
    )

    st.warning(
        "This tool does not constitute legal advice. "
        "Always consult a qualified attorney for binding decisions."
    )

# ─── Main Area ───────────────────────────────────────────────────────────────────
st.title("Paste your contract clause")
st.caption("Works with any language — employment, rental, NDA, freelance, SaaS.")

clause_input = st.text_area(
    label="Clause input",
    label_visibility="collapsed",
    placeholder=(
        "Paste your clause here... e.g. 'The Employee agrees to a non-compete period of "
        "24 months within a 50-mile radius of the Employer\\'s primary office...'"
    ),
    height=200,
    key="clause_input"
)

analyze_clicked = st.button("🔍 Analyze Clause", type="primary", use_container_width=True)

if analyze_clicked:
    # Validate
    if not clause_input or clause_input.strip() == "":
        st.error("Please paste a clause to analyze.")
        st.stop()
    elif len(clause_input.strip()) < 20:
        st.error("That's too short to be a clause.")
        st.stop()
    else:
        text_to_analyze = clause_input.strip()
        if len(text_to_analyze) > 8000:
            st.warning("Clause truncated to 8000 characters.")
            text_to_analyze = text_to_analyze[:8000]

        with st.spinner("Analyzing your clause..."):
            try:
                result = analyze_clause(text_to_analyze, contract_type, perspective)
            except Exception as e:
                st.error(f"API call failed: {str(e)}")
                st.stop()

        st.session_state["result"] = result
        st.session_state["last_clause"] = text_to_analyze

# ─── Results ─────────────────────────────────────────────────────────────────────
if st.session_state["result"] is not None:
    parsed = st.session_state["result"]

    plain_english = parsed.get("plain_english", "No explanation returned.")
    red_flags = parsed.get("red_flags", [])
    negotiation_tips = parsed.get("negotiation_tips", [])
    overall_risk = parsed.get("overall_risk", "UNKNOWN")
    clause_type = parsed.get("clause_type", "Unknown")

    tab1, tab2, tab3 = st.tabs(["📖 Plain English", "🚨 Red Flags", "🤝 Negotiate"])

    # ── Tab 1: Plain English ──────────────────────────────────────────────────────
    with tab1:
        st.subheader("What this clause actually means")
        st.markdown(plain_english)
        st.divider()

        risk_colors = {"HIGH": "#e74c3c", "MEDIUM": "#e67e22", "LOW": "#2ecc71"}
        risk_color = risk_colors.get(overall_risk, "#95a5a6")

        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Overall Risk Level", overall_risk)
        with col2:
            st.markdown(
                f"<div style='margin-top:8px;'>"
                f"<span style='background-color:{risk_color};color:white;"
                f"padding:6px 14px;border-radius:6px;font-weight:700;font-size:15px;'>"
                f"{overall_risk}</span>"
                f"&nbsp;&nbsp;<span style='color:#666;font-size:14px;'>Clause type: <b>{clause_type}</b></span>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ── Tab 2: Red Flags ──────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Watch out for these")
        if not red_flags:
            st.success("No significant red flags detected.")
        else:
            for i, flag in enumerate(red_flags):
                severity = flag.get("severity", "LOW")
                issue = flag.get("issue", "")
                explanation = flag.get("explanation", "")

                if severity == "HIGH":
                    st.error(f"🔴 HIGH: {issue}")
                elif severity == "MEDIUM":
                    st.warning(f"🟡 MEDIUM: {issue}")
                else:
                    st.info(f"🔵 LOW: {issue}")

                st.write(explanation)

                if i < len(red_flags) - 1:
                    st.divider()

    # ── Tab 3: Negotiate ──────────────────────────────────────────────────────────
    with tab3:
        st.subheader("How to push back")
        if not negotiation_tips:
            st.success("This clause appears reasonable. No major negotiation points.")
        else:
            for i, tip in enumerate(negotiation_tips):
                st.markdown(f"**Point:** {tip.get('point', '')}")
                st.code(tip.get("suggested_language", ""), language=None)
                if i < len(negotiation_tips) - 1:
                    st.divider()

    st.divider()
    if st.button("🔄 Analyze another clause"):
        st.session_state["result"] = None
        st.session_state["last_clause"] = ""
        st.rerun()

st.caption("⚡ Powered by Groq · LLaMA 3.3 70B")
