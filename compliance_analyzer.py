# -*- coding: utf-8 -*-
import os
import sys
import logging
import locale
import json
import requests
import unicodedata

# Strongly prefer UTF-8 everywhere at runtime (PYTHONIOENCODING only helps at process start)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # Fallback to environment variables for older Python versions

# Rebuild root logging with UTF-8 handlers
for h in list(logging.getLogger().handlers):
    logging.getLogger().removeHandler(h)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),                 # now UTF-8
        logging.FileHandler("app.log", encoding="utf-8"),  # force UTF-8 file
    ],
)

# Turn down noisy libraries that log raw payloads
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
# If OPENAI_LOG is set in your environment, neutralize it:
os.environ.pop("OPENAI_LOG", None)

# Helper for safely logging arbitrary text (escapes non-ASCII if your sinks regress)
def log_safe(prefix, text):
    try:
        logging.info("%s%s", prefix, text)
    except Exception:
        logging.info("%s%s", prefix, text.encode("unicode_escape").decode("ascii"))

# Environment defaults
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'en_US.UTF-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'

# Set UTF-8 locale for requests
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except Exception:
    pass

# For requests library
import requests
requests.models.Response.encoding = 'utf-8'

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY not found in environment variables")

# ASCII-only system prompt (no smart quotes, no em dashes, no special symbols)
SYSTEM_PROMPT = """You are ChatGPT (GPT-5) acting as a professional engineer conducting a technical review of product specifications for compliance with project requirements. Your job is single-purpose:

* Inputs: exactly two documents provided by the user:
  1. PROJECT_SPEC = the project specification / requirements (baseline).
  2. SUBMITTAL = the vendor's product specification sheet(s) / submittal package.
* Output: one and only one artifact -- a compliance review report in the exact structure and behavior defined below.
* Never produce any other content, code, UI, or explanations.

## Core Behavior Rules
* Be thorough, systematic, and technically rigorous.
* Do not assume values that are not explicitly stated in the documents. If a required spec is missing, mark INSUFFICIENT DATA.
* Cite both documents by page number and section (if available) and include short direct quotes (<=30 words) for critical specs.
* Use consistent units; convert where necessary, and show converted values in parentheses.
* Note tolerances, test conditions (e.g., "at 20 degrees C"), and footnotes/disclaimers that modify specs.
* If multiple models/variants exist in the SUBMITTAL, evaluate each model number separately.
* Use the marking system exactly as follows: [GREEN = MEETS/EXCEEDS], [YELLOW = MARGINAL], [RED = DOES NOT MEET], [GRAY = INSUFFICIENT DATA].
* Temperature set to 0 (deterministic). No chit-chat.

---
## Review Methodology (Follow These Steps Exactly)

### Step 1 - Initial Document Review
1. Identify all model numbers / product variants in SUBMITTAL (include every distinct model code).
2. Map the layout of technical data in both docs (tables, drawings, notes, footnotes).
3. List any footnotes, disclaimers, conditions, or test bases that affect specs (e.g., "all ratings at 68 degrees F", "typical values", "optional accessory").
4. Note document metadata: title, revision/date, and any version identifiers.

### Step 2 - Specification Extraction and Documentation
From PROJECT_SPEC (baseline requirements), extract requirements that apply; at minimum include (as applicable to the equipment type in SUBMITTAL):
* Physical: dimensions, tolerances, clearances, connections (size/rating), weight.
* Materials: material composition/grade (e.g., SA-516-70), corrosion allowances, coatings.
* Performance: capacity, pressure ratings, flow/heat input/efficiency, power, speed, turndown.
* Environmental: temperature/humidity ranges, UV/ingress ratings, noise, altitude, ambient bases.
* Compliance/Standards: ASME/ASTM/ISO/UL/NFPA/NEC/CE/etc., required code stamps, test/hydro.
* Safety factors & tests: design factors, hydro, NDE, factory/field tests, relief/safety settings.
* Controls/Instrumentation: control architecture (e.g., linkageless), I/O protocols (HART, Modbus), trim/analyzers, setpoints.
* Installation limits: orientation, supports, utilities, access, foundation, stack/vent, electrical.
* Warranty/Service Life: required durations, service intervals, spares, manuals.

From SUBMITTAL, extract the actual offered specifications for each Model Number/Variant across the same categories. Quote critical values with page/section references.

### Step 3 - Comparative Analysis
For each project requirement, find the matching SUBMITTAL spec and mark:
* EXCEEDS -> [GREEN] EXCEEDS
* MEETS -> [GREEN] MEETS
* MARGINAL (barely meets or conditional/footnote dependency) -> [YELLOW] MARGINAL
* DOES NOT MEET -> [RED] DOES NOT MEET
* Not stated / unclear -> [GRAY] INSUFFICIENT DATA
Explicitly list absent or ambiguous specs. Where conditional, quote the condition (e.g., "at 15% FGR").

### Step 4 - Compliance Assessment (Per Model)
Choose one status per model:
* COMPLIANT -- meets or exceeds all specified requirements.
* PARTIALLY COMPLIANT -- meets some but not all (list deficiencies).
* NON-COMPLIANT -- fails to meet one or more critical requirements.
* INSUFFICIENT DATA -- missing info prevents a determination.

---
## Strict Output Format (Use Exactly This Markdown Structure)

# Executive Summary
* Overall compliance status: [Compliant / Partially Compliant / Non-Compliant / Insufficient Data]
* Number of models reviewed: [N]
* Number of compliant models identified: [N]

# Detailed Analysis by Model Number
## Model: [MODEL NUMBER EXACTLY AS IN SUBMITTAL]
Compliance Status: [Compliant / Partially Compliant / Non-Compliant / Insufficient Data]

Specification Review (Project Requirement -> Actual Spec -> Status):
* [Requirement A]: "[Actual value/description + unit]" (SUBMITTAL p.X section Y; quote <=30w). Status: [GREEN/YELLOW/RED/GRAY: MEETS/EXCEEDS/DOES NOT MEET/INSUFFICIENT DATA].
  Reference: PROJECT_SPEC p.X section Y (quote <=30w).
* [Requirement B]: ...
* (Continue for all applicable requirements, including dimensions, materials, performance, environmental, codes, safety factors/tests, installation, warranty.)

Critical Observations:
* [Short bullets on limitations, ambiguous clauses, footnotes impacting compliance, or data that appears inconsistent across pages/tables.]
* [Note any assumptions required due to missing data.]

# Risk Assessment
* Marginally met specifications (YELLOW): [List items; explain why marginal.]
* Missing critical information (GRAY): [List items and why they are critical.]
* Potential compatibility/integration issues: [Controls/I-O, mechanical interfaces, electrical, stack/venting, foundation, etc.]

# Compliance Assessment (by model)
* [MODEL NUMBER] -- [Final status with one-sentence rationale.]

# Engineering Recommendations
* Recommended model(s) for procurement: [If any; otherwise state none.]
* Additional testing/verification needed: [Factory tests, field acceptance, emissions, hydro/NDE, performance curves, etc.]
* Suggested alternatives: [If no models fully comply, suggest practical alternatives or conditions for acceptance.]

# Critical Considerations
* Safety Margins: [Evaluate stated safety factors; relief settings vs. max conditions; code stamps.]
* Environmental Conditions: [Check ambient/test bases vs. actual site conditions; derates.]
* Codes & Standards: [Confirm ASME/ASTM/ISO/UL/NFPA/NEC/etc.; list missing declarations.]
* Lifecycle Considerations: [Maintenance access, spares, coatings/materials, service intervals, warranty.]
* Interoperability: [Mechanical interfaces, utilities, controls protocols (HART/Modbus), networking, DCS.]

# Documentation Requirements
* PROJECT_SPEC citation list: [Page and section for every critical requirement referenced.]
* SUBMITTAL citation list: [Page and section for every matched spec; include drawing/table IDs if present.]
* Direct quotes for critical specs: [<=30 words each, with page/section.]
* Document metadata: [Titles, revision numbers/dates for both documents.]
* Assumptions made: [Only if required by missing or ambiguous information.]

# Quality Assurance Checklist
* [CHECK] All model numbers/variants evaluated
* [CHECK] Every project requirement addressed
* [CHECK] Units standardized; conversions shown
* [CHECK] Tolerances and test conditions noted (e.g., "at 20 degrees C", "sea level")
* [CHECK] Conditional specifications and footnotes called out
* [CHECK] Professional engineering judgment applied to marginal cases

---
## Additional Parsing & Evaluation Rules
* Tables & Drawings: If specs appear only in drawings/GA tables, extract values and name the drawing/table ID.
* Footnotes/Disclaimers: If a spec is contingent (e.g., "typical" or "optional"), mark [YELLOW] MARGINAL unless the required option is explicitly included.
* Conflicts: If two locations in SUBMITTAL conflict, note both, mark [YELLOW] and explain.
* Unit Handling: Convert to the PROJECT_SPEC's primary system (SI or USC). Example: 2 in (50.8 mm).
* Emissions/Performance Curves: If PROJECT_SPEC requires multi-point performance/emissions and SUBMITTAL omits points, mark [GRAY] and list missing points explicitly.
* Standards/Certifications: If a code stamp/listing is required (e.g., ASME Section I, UL, NFPA 70) and SUBMITTAL only states "designed to", mark [YELLOW] until explicit certification evidence is shown.
* Warranty/Service Life: If not stated or shorter than required, mark [RED] (if critical) or [YELLOW] (if acceptable with conditions).
* Installation Limits: Validate clearances, supports, stack/vent geometry, electrical ratings; flag interfaces needing RFI.
* No Hallucinations: If not found in either document, do not invent a value; mark [GRAY].

---
## Input Contract (How to Treat Uploaded Files)
* Treat the first uploaded file as PROJECT_SPEC and the second as SUBMITTAL.
* If PDFs include images/tables, infer text from the provided content; if a page number is not available, cite the nearest identifiable section/heading or table/drawing title.
* Do not echo full documents; include only short quotes (<=30 words) as evidence.

---
## Output Constraints
* Output only the report in the Strict Output Format above.
* Do not include instructions, prefaces, or closing remarks.
* Keep the Executive Summary concise (approximately 120-180 words).
* Make statuses explicit with the bracketed color tags: [GREEN] [YELLOW] [RED] [GRAY] for every requirement line.
"""

def analyze_compliance(project_spec_text, vendor_submittal_text):
    """
    Analyze compliance between project specification and vendor submittal using OpenAI.
    All strings are sanitized to ASCII for safety.
    """
    if not OPENAI_API_KEY:
        raise ValueError(
            "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )

    # Enhanced clean_text function with aggressive cleaning
    def clean_text(text):
        if not isinstance(text, str):
            return ""
        
        # First pass: Replace common Unicode characters
        replacements = {
            '\u2019': "'",  # right single quote
            '\u2018': "'",  # left single quote
            '\u201c': '"',  # left double quote
            '\u201d': '"',  # right double quote
            '\u2013': '-',  # en dash
            '\u2014': '--', # em dash
            '\u2026': '...',# ellipsis
            '\u00b0': ' deg', # degree
            '\u00bd': '1/2',
            '\u00bc': '1/4',
            '\u00be': '3/4',
            '\u2022': '*',  # bullet
            '\u00b7': '*',  # middle dot
            '\u2032': "'",  # prime
            '\u2033': '"',  # double prime
            '\u00a0': ' ',  # non-breaking space
            '\t': ' ',      # tab
            '\r': '',       # carriage return
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Second pass: Normalize Unicode decomposition
        try:
            text = unicodedata.normalize('NFKD', text)
        except Exception:
            pass
        
        # Third pass: Convert to ASCII bytes and back to remove all non-ASCII
        try:
            text = text.encode('ascii', errors='ignore').decode('ascii')
        except Exception:
            # Fallback: manually strip non-ASCII characters
            text = ''.join(ch for ch in text if ord(ch) < 128)
        
        # Final aggressive cleanup - remove any remaining non-printable chars
        import string
        printable = set(string.printable)
        text = ''.join(filter(lambda x: x in printable, text))
        
        # Remove any null bytes or control characters
        text = text.replace('\x00', '')
        text = ''.join(ch for ch in text if ord(ch) >= 32 or ch in '\n\r\t')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        return text

    project_spec_text = clean_text(project_spec_text)
    vendor_submittal_text = clean_text(vendor_submittal_text)

    user_message = f"""PROJECT_SPEC:
{project_spec_text}

---

SUBMITTAL:
{vendor_submittal_text}"""

    try:
        logging.info("Sending compliance analysis request to OpenAI...")

        # Clean the system prompt and the user message to ensure ASCII
        clean_system_prompt = clean_text(SYSTEM_PROMPT)
        clean_user_message = clean_text(user_message)
        
        # Ensure the text is properly encoded as UTF-8 bytes then decoded
        # This helps ensure clean UTF-8 strings
        clean_system_prompt = clean_system_prompt.encode('utf-8', errors='ignore').decode('utf-8')
        clean_user_message = clean_user_message.encode('utf-8', errors='ignore').decode('utf-8')
        
        # STEP 1 - Debug initial cleaning
        log_safe("STEP 1 - Initial cleaning complete. System prompt length: ", str(len(clean_system_prompt)))
        log_safe("STEP 1 - User message length: ", str(len(clean_user_message)))
        
        # Debug: Check for Unicode in original SYSTEM_PROMPT
        logging.info("DEBUG: Checking raw SYSTEM_PROMPT for Unicode...")
        for i, ch in enumerate(SYSTEM_PROMPT[:50]):
            if ord(ch) > 127:
                logging.error(f"FOUND UNICODE IN RAW SYSTEM_PROMPT at position {i}: {ch!r} (U+{ord(ch):04X})")
                break
        
        # Debug: Check for Unicode in cleaned system prompt
        logging.info("DEBUG: Checking cleaned system prompt for Unicode...")
        for i, ch in enumerate(clean_system_prompt[:50]):
            if ord(ch) > 127:
                logging.error(f"FOUND UNICODE IN CLEANED SYSTEM_PROMPT at position {i}: {ch!r} (U+{ord(ch):04X})")
                break

        log_safe("STEP 2 - UTF-8 encoding/decoding complete. System prompt length: ", str(len(clean_system_prompt)))
        log_safe("STEP 2 - User message length: ", str(len(clean_user_message)))

        # STEP 3 - Prepare the payload
        logging.info("STEP 3 - Preparing JSON payload...")
        payload = {
            "model": "gpt-4o",  # Use gpt-4o which has 128K token context window for large documents
            "messages": [
                {"role": "system", "content": clean_system_prompt},
                {"role": "user", "content": clean_user_message}
            ],
            "temperature": 0,
            "max_completion_tokens": 8000
        }
        
        # Comprehensive debugging - check every string in payload
        logging.info("DEBUG: Checking all payload strings for Unicode...")
        for key, value in payload.items():
            if isinstance(value, str):
                for i, ch in enumerate(value):
                    if ord(ch) > 127:
                        logging.error(f"FOUND UNICODE IN PAYLOAD[{key}] at position {i}: {ch!r} (U+{ord(ch):04X})")
                        break
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        for sub_key, sub_value in item.items():
                            if isinstance(sub_value, str):
                                for i, ch in enumerate(sub_value):
                                    if ord(ch) > 127:
                                        logging.error(f"FOUND UNICODE IN PAYLOAD[{key}][{idx}][{sub_key}] at position {i}: {ch!r} (U+{ord(ch):04X})")
                                        break

        # Assertion to verify ASCII-only content
        def assert_ascii(s, label=""):
            if isinstance(s, str):
                bad = [(i, ch, ord(ch)) for i, ch in enumerate(s) if ord(ch) >= 128]
                if bad:
                    raise ValueError(f"Non-ASCII in {label}: first few -> {bad[:5]}")

        assert_ascii(clean_system_prompt, "system")
        assert_ascii(clean_user_message, "user")

        # STEP 4 - Final check for non-ASCII characters
        logging.info("DEBUG: Final check for non-ASCII characters...")
        try:
            for i, ch in enumerate(clean_user_message):
                if ord(ch) > 127:
                    logging.error(f"Found non-ASCII in clean_user_message at position {i}: {ch!r} (U+{ord(ch):04X})")
                    # Log context around the problematic character
                    start = max(0, i-20)
                    end = min(len(clean_user_message), i+20)
                    logging.error(f"Context: ...{clean_user_message[start:end]!r}...")
                    break
            
            for i, ch in enumerate(clean_system_prompt):
                if ord(ch) > 127:
                    logging.error(f"Found non-ASCII in clean_system_prompt at position {i}: {ch!r} (U+{ord(ch):04X})")
                    # Log context around the problematic character
                    start = max(0, i-20)
                    end = min(len(clean_system_prompt), i+20)
                    logging.error(f"Context: ...{clean_system_prompt[start:end]!r}...")
                    break
        except Exception as e:
            logging.error(f"Debug check failed: {e}")
            
        # STEP 5 - Use requests directly for complete encoding control
        logging.info("STEP 5 - Creating HTTP session...")
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json; charset=utf-8"  # Explicitly set UTF-8
        })

        # STEP 6 - Manually encode the JSON payload to ensure UTF-8
        logging.info("STEP 6 - Encoding JSON payload...")
        try:
            json_payload = json.dumps(payload, ensure_ascii=True)  # Force ASCII in JSON
            logging.info(f"STEP 6 - JSON payload created successfully. Length: {len(json_payload)}")
            logging.info(f"STEP 6 - First 200 chars of JSON: {json_payload[:200]}")
        except Exception as json_error:
            logging.error(f"STEP 6 - JSON encoding failed: {json_error}")
            # Try to identify which field caused the issue
            for key, value in payload.items():
                try:
                    test_json = json.dumps({key: value}, ensure_ascii=True)
                    logging.info(f"STEP 6 - Field '{key}' encoded successfully")
                except Exception as field_error:
                    logging.error(f"STEP 6 - Field '{key}' failed to encode: {field_error}")
            raise
        
        logging.info("STEP 7 - Making HTTP request...")
        try:
            # Let requests handle the encoding - don't double-encode
            response = session.post(
                "https://api.openai.com/v1/chat/completions",
                data=json_payload,  # Pass the JSON string directly, let requests encode it
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=90
            )
            logging.info(f"STEP 7 - HTTP request completed. Status: {response.status_code}")
        except Exception as http_error:
            logging.error(f"STEP 7 - HTTP request failed: {http_error}")
            # Try alternative approach with json parameter
            logging.info("STEP 7 - Trying alternative approach with json parameter...")
            try:
                response = session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,  # Let requests handle JSON encoding completely
                    timeout=90
                )
                logging.info(f"STEP 7 - Alternative approach succeeded. Status: {response.status_code}")
            except Exception as alt_error:
                logging.error(f"STEP 7 - Alternative approach also failed: {alt_error}")
                raise

        if response.status_code != 200:
            # Avoid logging raw response.text if your sink is not UTF-8
            log_safe("OpenAI API error body: ", response.text)
            raise Exception(f"OpenAI API error: {response.status_code}")

        result_json = response.json()
        result = result_json['choices'][0]['message']['content']
        logging.info("Compliance analysis completed successfully")
        return result

    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        raise Exception(f"Failed to analyze compliance: {str(e)}")
