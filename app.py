import streamlit as st
import ollama
import json
import os
import re
from datetime import datetime, timedelta

symptoms = ["fever", "cough", "headache", "nausea", "fatigue", "dizziness", "shortness of breath", 
            "chest pain", "abdominal pain", "diarrhea", "vomiting", "sore throat", "runny nose", 
            "muscle aches", "joint pain", "rash", "swelling", "weight loss", "weight gain", 
            "night sweats", "chills", "edema", "orthopnea", "reduced urine output", "back pain", "neck pain",
            "insomnia", "anxiety", "panic attacks", "mood swings", "sadness", "hopelessness", 
            "loss of interest", "difficulty concentrating", "memory problems", "restlessness", 
            "irritability", "suicidal thoughts", "hallucinations", "paranoia", "racing thoughts",
            "appetite changes", "social withdrawal", "excessive worry",
            "pelvic pain", "abnormal vaginal bleeding", "missed period", "irregular periods", 
            "heavy menstrual bleeding", "painful periods", "vaginal discharge", "painful intercourse",
            "breast pain", "breast lumps", "hot flashes", "vaginal itching", "vaginal dryness",
            "spotting between periods", "postmenopausal bleeding", "painful urination", "frequent urination",
            "lower back pain", "bloating", "constipation", "painful bowel movements during period",
            "painful ovulation", "breast tenderness", "nipple discharge", "vulvar pain",
            "burning sensation during urination", "urgency to urinate"]

mods = ["mild", "moderate", "severe", "intermittent", "constant", "sudden onset", "gradual onset", 
        "worsening", "improving", "persistent", "recurring", "sharp", "dull", "throbbing", 
        "burning", "stabbing", "cramping"]

past = ["diabetes", "hypertension", "asthma", "heart disease", "cancer", "stroke", "kidney disease", 
        "liver disease", "COPD", "arthritis", "depression", "anxiety", "thyroid disorder", 
        "autoimmune disease", "allergies", "previous surgeries", "cardiomyopathy",
        "bipolar disorder", "schizophrenia", "PTSD", "OCD", "panic disorder", "eating disorder",
        "ADHD", "autism", "personality disorder", "substance abuse disorder",
        "on antidepressants", "on antipsychotics", "on mood stabilizers", "on anti-anxiety medication",
        "PCOS", "endometriosis", "fibroids", "ovarian cysts", "menopause", "pregnancy complications",
        "previous miscarriage", "infertility", "cervical dysplasia", "on birth control",
        "pelvic inflammatory disease", "adenomyosis", "uterine prolapse", "ovarian cancer",
        "breast cancer", "cervical cancer", "endometrial cancer", "HPV", "sexually transmitted infection",
        "gestational diabetes", "preeclampsia", "ectopic pregnancy", "cesarean section",
        "hysterectomy", "tubal ligation"]

habits = ["smoking", "alcohol", "drug use", "vaping", "tobacco chewing"]

def calculate_pain_score(pain_level, pain_description=""):
    pain_map = {
        "no pain": 0,
        "mild": 2,
        "moderate": 5,
        "severe": 8,
        "worst pain ever": 10,
        "unbearable": 10
    }
    
    score = 0
    for key, value in pain_map.items():
        if key in pain_level.lower():
            score = value
            break
    
    descriptors_high = ["sharp", "stabbing", "burning", "worst", "unbearable"]
    descriptors_low = ["dull", "aching", "minor"]
    
    if any(desc in pain_description.lower() for desc in descriptors_high):
        score = min(10, score + 1)
    elif any(desc in pain_description.lower() for desc in descriptors_low):
        score = max(0, score - 1)
    
    return score

def calculate_habit_risk_score(patient_info):
    risk_score = 0
    habits_data = patient_info.get("habits", {})
    symptoms_list = patient_info.get("symptoms", [])
    
    if habits_data.get("smoking"):
        smoking_status = habits_data.get("smoking_details", {})
        years = smoking_status.get("years", 0)
        packs_per_day = smoking_status.get("packs_per_day", 0)
        pack_years = years * packs_per_day
        
        base_score = 0
        if pack_years > 30:
            base_score = 5
        elif pack_years > 20:
            base_score = 4
        elif pack_years > 10:
            base_score = 3
        elif pack_years > 5:
            base_score = 2
        else:
            base_score = 1
        
        if any(s in symptoms_list for s in ["shortness of breath", "chest pain", "cough"]):
            base_score *= 1.5
        
        risk_score += base_score
    
    if habits_data.get("vaping"):
        risk_score += 2
        if "shortness of breath" in symptoms_list or "chest pain" in symptoms_list:
            risk_score += 2
    
    if habits_data.get("alcohol"):
        alcohol_status = habits_data.get("alcohol_details", {})
        drinks_per_week = alcohol_status.get("drinks_per_week", 0)
        
        if drinks_per_week > 14:
            risk_score += 3
        elif drinks_per_week > 7:
            risk_score += 2
        else:
            risk_score += 1
        
        if any(s in symptoms_list for s in ["abdominal pain", "nausea", "vomiting"]):
            risk_score += 2
    
    if habits_data.get("drug_use"):
        risk_score += 4
        if any(s in symptoms_list for s in ["chest pain", "dizziness", "anxiety"]):
            risk_score += 3
    
    return round(risk_score, 1)

def triage(txt):
    score = 0
    try:
        s = txt.find('{')
        e = txt.rfind('}') + 1
        data = json.loads(txt[s:e])
    except:
        return 0, {}
    
    sc = {"fever": 2, "cough": 1, "shortness of breath": 3, "chest pain": 3, "abdominal pain": 2, 
          "diarrhea": 1, "vomiting": 1, "sore throat": 1, "runny nose": 1, "muscle aches": 1, 
          "joint pain": 1, "rash": 2, "swelling": 2, "weight loss": 2, "weight gain": 1, 
          "night sweats": 2, "chills": 1, "edema": 2, "orthopnea": 3, "reduced urine output": 3, 
          "dizziness": 2, "nausea": 1, "back pain": 2, "neck pain": 2,
          "insomnia": 1, "anxiety": 2, "panic attacks": 3, "mood swings": 2, "sadness": 1,
          "hopelessness": 3, "loss of interest": 2, "difficulty concentrating": 1, "memory problems": 2,
          "restlessness": 1, "irritability": 1, "suicidal thoughts": 5, "hallucinations": 4,
          "paranoia": 3, "racing thoughts": 2, "appetite changes": 1, "social withdrawal": 2,
          "excessive worry": 2,
          "pelvic pain": 2, "abnormal vaginal bleeding": 3, "missed period": 1,
          "irregular periods": 1, "heavy menstrual bleeding": 2, "painful periods": 1, 
          "vaginal discharge": 1, "painful intercourse": 1, "breast pain": 1, "breast lumps": 3,
          "hot flashes": 1, "vaginal itching": 1, "vaginal dryness": 1,
          "spotting between periods": 2, "postmenopausal bleeding": 3, "painful urination": 2,
          "frequent urination": 1, "lower back pain": 1, "bloating": 1, "constipation": 1,
          "painful bowel movements during period": 2, "painful ovulation": 1, "breast tenderness": 1,
          "nipple discharge": 2, "vulvar pain": 2, "burning sensation during urination": 2,
          "urgency to urinate": 1}
    
    for s in data.get("symptoms", []):
        if s in sc:
            score += sc[s]
    
    ms = {"mild": 1, "moderate": 2, "severe": 3, "intermittent": 1, "constant": 2, "sudden onset": 3, 
          "gradual onset": 1, "worsening": 2, "improving": -1, "persistent": 2, "recurring": 1, 
          "sharp": 2, "stabbing": 3, "burning": 2, "throbbing": 1, "cramping": 1}
    for m in data.get("modifiers", []):
        if m in ms:
            score += ms[m]
    
    pain_score = data.get("pain_score", 0)
    if pain_score:
        if pain_score >= 8:
            score += 5
        elif pain_score >= 6:
            score += 3
        elif pain_score >= 4:
            score += 2
        else:
            score += 1
    
    age = data.get("age", "")
    if age:
        try:
            a = int(age)
            if a >= 60:
                score *= 1.5 + (a - 60) / 10
            elif a < 2:
                score *= 1.3
        except:
            pass
    
    ps = {"diabetes": 2, "hypertension": 2, "asthma": 2, "heart disease": 3, "cancer": 3, 
          "stroke": 3, "kidney disease": 3, "liver disease": 3, "COPD": 3, "arthritis": 1, 
          "depression": 2, "anxiety": 2, "thyroid disorder": 1, "autoimmune disease": 2, 
          "allergies": 1, "previous surgeries": 1, "cardiomyopathy": 3,
          "bipolar disorder": 3, "schizophrenia": 3, "PTSD": 2, "OCD": 2, "panic disorder": 2,
          "eating disorder": 2, "ADHD": 1, "autism": 1, "personality disorder": 2,
          "substance abuse disorder": 3, "on antidepressants": 2, "on antipsychotics": 2,
          "on mood stabilizers": 2, "on anti-anxiety medication": 1,
          "PCOS": 1, "endometriosis": 2, "fibroids": 1, "ovarian cysts": 1, "menopause": 1,
          "pregnancy complications": 2, "previous miscarriage": 1, "infertility": 1,
          "cervical dysplasia": 2, "on birth control": 1, "pelvic inflammatory disease": 2,
          "adenomyosis": 2, "uterine prolapse": 2, "ovarian cancer": 3, "breast cancer": 3,
          "cervical cancer": 3, "endometrial cancer": 3, "HPV": 1, "sexually transmitted infection": 2,
          "gestational diabetes": 2, "preeclampsia": 3, "ectopic pregnancy": 3}
    for p in data.get("past_medical_history", []):
        if p in ps:
            score += ps[p]
    
    psychiatric_meds = ["on antidepressants", "on antipsychotics", "on mood stabilizers", "on anti-anxiety medication"]
    mental_health_symptoms = ["suicidal thoughts", "hallucinations", "paranoia", "panic attacks", 
                              "hopelessness", "anxiety", "mood swings", "sadness", "insomnia",
                              "loss of interest", "social withdrawal"]
    
    has_psych_meds = any(med in data.get("past_medical_history", []) for med in psychiatric_meds)
    has_mental_symptoms = any(symptom in data.get("symptoms", []) for symptom in mental_health_symptoms)
    
    if has_psych_meds and has_mental_symptoms:
        score += 3
    
    habits_risk = calculate_habit_risk_score(data)
    score += habits_risk
    
    return round(score, 1), data

def doc(score):
    speciality = {
        "Cardiology": ["chest pain", "shortness of breath", "orthopnea", "edema"],
        "Pulmonology": ["shortness of breath", "cough", "orthopnea"],
        "Gastroenterology": ["abdominal pain", "diarrhea", "vomiting", "nausea"],
        "Neurology": ["headache", "dizziness", "neck pain", "memory problems"],
        "Infectious Disease": ["fever", "chills", "night sweats"],
        "Rheumatology": ["joint pain", "muscle aches", "rash"],
        "Endocrinology": ["weight loss", "weight gain", "fatigue"],
        "Nephrology": ["reduced urine output", "edema"],
        "Psychiatry": ["anxiety", "depression", "panic attacks", "mood swings", "insomnia",
                      "hopelessness", "suicidal thoughts", "hallucinations", "paranoia",
                      "loss of interest", "racing thoughts", "social withdrawal", "excessive worry",
                      "irritability", "restlessness", "sadness", "difficulty concentrating"],
        "Gynecology": ["pelvic pain", "abnormal vaginal bleeding", "missed period", "irregular periods",
                      "heavy menstrual bleeding", "painful periods", "vaginal discharge", 
                      "painful intercourse", "breast pain", "breast lumps", "hot flashes",
                      "vaginal itching", "vaginal dryness", "spotting between periods",
                      "postmenopausal bleeding", "painful ovulation", "breast tenderness",
                      "nipple discharge", "vulvar pain"],
        "Urology": ["painful urination", "frequent urination", "burning sensation during urination",
                   "urgency to urinate", "reduced urine output"],
        "ENT": ["sore throat", "runny nose"],
        "Dermatology": ["rash", "swelling"],
        "Orthopedics": ["joint pain", "muscle aches", "back pain"],
        "General Medicine": ["fever", "cough", "headache", "nausea", "fatigue"]
    }
    
    matched = []
    for specialty, syms in speciality.items():
        if any(sym in syms for sym in score.get("symptoms", [])):
            matched.append(specialty)
    
    seen = set()
    matched_unique = []
    for specialty in matched:
        if specialty not in seen:
            seen.add(specialty)
            matched_unique.append(specialty)
    
    return matched_unique[0:3] if matched_unique else ["General Medicine"]

def get_possible_diagnoses(patient_info):
    symptoms_list = patient_info.get("symptoms", [])
    modifiers = patient_info.get("modifiers", [])
    past_history = patient_info.get("past_medical_history", [])
    age = patient_info.get("age", "")
    habits_data = patient_info.get("habits", {})
    
    diagnoses = []
    
    if "chest pain" in symptoms_list:
        if "shortness of breath" in symptoms_list or "severe" in modifiers:
            diagnoses.append({
                "condition": "Acute Coronary Syndrome / Heart Attack",
                "reasoning": "Chest pain with shortness of breath is a critical cardiac warning sign",
                "urgency": "EMERGENCY"
            })
        if "heart disease" in past_history or habits_data.get("smoking"):
            diagnoses.append({
                "condition": "Angina Pectoris",
                "reasoning": "History of heart disease or smoking increases risk of cardiac chest pain",
                "urgency": "URGENT"
            })
    
    if "shortness of breath" in symptoms_list:
        if "asthma" in past_history or "COPD" in past_history:
            diagnoses.append({
                "condition": "Asthma Exacerbation / COPD Exacerbation",
                "reasoning": "Known respiratory condition with worsening symptoms",
                "urgency": "URGENT"
            })
        if "fever" in symptoms_list and "cough" in symptoms_list:
            diagnoses.append({
                "condition": "Pneumonia",
                "reasoning": "Combination of fever, cough, and breathing difficulty suggests lung infection",
                "urgency": "URGENT"
            })
    
    if "abdominal pain" in symptoms_list:
        if "severe" in modifiers and "sudden onset" in modifiers:
            diagnoses.append({
                "condition": "Acute Appendicitis / Bowel Obstruction",
                "reasoning": "Severe, sudden abdominal pain requires urgent evaluation",
                "urgency": "EMERGENCY"
            })
        if "nausea" in symptoms_list and "vomiting" in symptoms_list:
            diagnoses.append({
                "condition": "Gastroenteritis / Food Poisoning",
                "reasoning": "Abdominal pain with nausea and vomiting suggests GI infection",
                "urgency": "LESS URGENT"
            })
    
    if "headache" in symptoms_list:
        if "severe" in modifiers and "sudden onset" in modifiers:
            diagnoses.append({
                "condition": "Subarachnoid Hemorrhage / Stroke",
                "reasoning": "Sudden severe 'thunderclap' headache is a medical emergency",
                "urgency": "EMERGENCY"
            })
        else:
            diagnoses.append({
                "condition": "Tension Headache / Migraine",
                "reasoning": "Most common types of headache",
                "urgency": "LESS URGENT"
            })
    
    if "pelvic pain" in symptoms_list:
        if "abnormal vaginal bleeding" in symptoms_list or "severe" in modifiers:
            diagnoses.append({
                "condition": "Ectopic Pregnancy / Ovarian Torsion",
                "reasoning": "Severe pelvic pain with bleeding requires urgent evaluation",
                "urgency": "EMERGENCY"
            })
        if "PCOS" in past_history or "endometriosis" in past_history:
            diagnoses.append({
                "condition": "PCOS/Endometriosis Flare",
                "reasoning": "Known gynecological condition with worsening symptoms",
                "urgency": "URGENT"
            })
    
    if "breast lumps" in symptoms_list:
        diagnoses.append({
            "condition": "Breast Mass (Requires Evaluation)",
            "reasoning": "Any breast lump requires clinical examination and imaging",
            "urgency": "URGENT"
        })
    
    if "fever" in symptoms_list:
        if "chills" in symptoms_list and "night sweats" in symptoms_list:
            diagnoses.append({
                "condition": "Severe Infection / Sepsis",
                "reasoning": "Fever with chills and night sweats indicates significant infection",
                "urgency": "URGENT"
            })
        else:
            diagnoses.append({
                "condition": "Viral Infection / Flu",
                "reasoning": "Fever is common with viral illnesses",
                "urgency": "LESS URGENT"
            })
    
    if not diagnoses:
        diagnoses.append({
            "condition": "Non-specific Symptoms",
            "reasoning": "Symptoms require clinical evaluation for accurate diagnosis",
            "urgency": "LESS URGENT"
        })

    urgency_order = {"EMERGENCY": 0, "URGENT": 1, "LESS URGENT": 2, "NON-URGENT": 3}
    diagnoses.sort(key=lambda x: urgency_order.get(x["urgency"], 4))
    
    return diagnoses[:5]

def get_specialty_reasoning(specialty, symptoms, past_history, habits):
    reasons = {
        "Cardiology": "Heart and cardiovascular system evaluation needed",
        "Pulmonology": "Lung and respiratory system assessment required",
        "Gastroenterology": "Digestive system evaluation needed",
        "Neurology": "Nervous system assessment required",
        "Infectious Disease": "Specialized evaluation for infection symptoms",
        "Rheumatology": "Joint, muscle, and autoimmune condition assessment",
        "Endocrinology": "Hormonal and metabolic system evaluation",
        "Nephrology": "Kidney function assessment needed",
        "Psychiatry": "Mental health evaluation and treatment needed",
        "Gynecology": "Women's reproductive health evaluation needed",
        "Urology": "Urinary system evaluation needed",
        "ENT": "Ear, nose, and throat evaluation",
        "Dermatology": "Skin condition evaluation",
        "Orthopedics": "Bone, joint, and musculoskeletal assessment",
        "General Medicine": "Comprehensive medical evaluation"
    }
    return reasons.get(specialty, "Specialized medical evaluation recommended")

def doctors():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "doctors.json")
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data['doctors']
    except:
        return []

def extract_with_llm(text, conversation_history=""):
    full_context = text
    if conversation_history:
        full_context = f"{text}\n\nAdditional Information:\n{conversation_history}"
    
    prompt = f"""You are a medical information extraction system. Your task is to analyze patient text and extract structured data with high precision.

INPUT TEXT:
{full_context}

EXTRACTION RULES:
1. Extract ONLY information explicitly stated in the text
2. Map extracted terms to the closest match from the allowed lists below
3. If no close match exists in an allowed list, omit that item
4. Do not infer, assume, or add information not present in the source text
5. Preserve clinical accuracy - if uncertain about a mapping, omit it

ALLOWED VALUES:

Symptoms (select all that apply):
{symptoms}

Modifiers (select all that apply):
{mods}

Past Medical Conditions (select all that apply):
{past}

EXTRACTION TARGETS:
- symptoms: List of current symptoms from allowed symptoms list
- modifiers: Qualifying terms (severity, frequency, location) from allowed modifiers list
- past_medical_history: Previous diagnoses/conditions from allowed conditions list
- duration: How long symptoms have been present (extract exact phrase, e.g., "3 days", "2 weeks")
- age: Patient age (number only, e.g., "45")
- gender: Patient gender (e.g., "male", "female", "non-binary", or null if not stated)

OUTPUT FORMAT:
Return ONLY valid JSON with this exact structure (no additional text):
{{
  "symptoms": [],
  "modifiers": [],
  "past_medical_history": [],
  "duration": "",
  "age": "",
  "gender": ""
}}

Now extract from the input text above."""
    
    try:
        res = ollama.generate(model="mistral:7b", prompt=prompt)
        return res['response']
    except:
        return "{}"

def is_pediatric_patient(age_str):
    try:
        age = int(age_str)
        return age < 18
    except:
        return "month" in age_str.lower()

def is_appropriate_for_guardian_questions(age_str):
    try:
        age = int(age_str)
        return age < 13
    except:
        return True

def format_question(question, is_guardian_context):
    if is_guardian_context:
        question = question.replace("Do you", "Does the patient")
        question = question.replace("Are you", "Is the patient")
        question = question.replace("Have you", "Has the patient")
        question = question.replace("your", "the patient's")
        question = question.replace("Your", "The patient's")
    return question

def check_logical_inconsistencies(patient_info, new_answer, question_key):
    symptoms_list = patient_info.get("symptoms", [])
    modifiers = patient_info.get("modifiers", [])
    age = patient_info.get("age", "")
    
    is_pediatric = is_pediatric_patient(age) if age else False
    is_guardian = is_appropriate_for_guardian_questions(age) if age else False
    pain_symptoms = ["chest pain", "abdominal pain", "headache", "back pain", "pelvic pain"]
    has_pain = any(pain in symptoms_list for pain in pain_symptoms)
    
    if has_pain and "pain_scale" not in st.session_state.asked_questions:
        question = "On a scale of 0-10, where 0 is no pain and 10 is the worst pain imaginable, how would you rate the pain?"
        return [("pain_scale", format_question(question, is_guardian))]

    if not is_pediatric:
        try:
            age_num = int(age) if age else 0
            if 15 <= age_num <= 50 and patient_info.get("gender", "").lower() in ["female", "f", "woman"]:
                if any(s in symptoms_list for s in ["nausea", "vomiting", "fatigue", "missed period", "pelvic pain"]):
                    if "pregnancy_possibility" not in st.session_state.asked_questions:
                        return [("pregnancy_possibility", "Is there any possibility of pregnancy?")]
        except:
            pass
    
    return []

def get_follow_up_question(patient_info, asked_questions):
    age = patient_info.get("age", "")
    is_guardian = is_appropriate_for_guardian_questions(age) if age else False

    logical_questions = check_logical_inconsistencies(patient_info, "", "")
    if logical_questions:
        return logical_questions[0]
    if "age" not in asked_questions and not patient_info.get("age"):
        return ("age", "What is the patient's age?")
    
    if "gender" not in asked_questions and not patient_info.get("gender"):
        return ("gender", "What is the patient's gender? (male/female/other)")
    
    if "duration" not in asked_questions and not patient_info.get("duration"):
        question = "How long have the symptoms been present?"
        return ("duration", format_question(question, is_guardian))
    
    if "modifiers" not in asked_questions and not patient_info.get("modifiers") and patient_info.get("symptoms"):
        symptom = patient_info['symptoms'][0] if patient_info['symptoms'] else 'symptoms'
        question = f"How would you describe the severity of the {symptom}? (mild/moderate/severe)"
        return ("modifiers", format_question(question, is_guardian))
    
    if "past_medical_history" not in asked_questions and not patient_info.get("past_medical_history"):
        question = "Are there any existing medical conditions or chronic illnesses?"
        return ("past_medical_history", format_question(question, is_guardian))
    
    if "current_medications" not in asked_questions:
        question = "Are you currently taking any medications? If yes, please list them."
        return ("current_medications", format_question(question, is_guardian))
    
    if "allergies" not in asked_questions:
        question = "Do you have any known allergies (medications, food, environmental)?"
        return ("allergies", format_question(question, is_guardian))
    
    if "recent_travel" not in asked_questions:
        question = "Have you traveled recently or been exposed to anyone who is sick?"
        return ("recent_travel", format_question(question, is_guardian))
    
    if "symptom_triggers" not in asked_questions and patient_info.get("symptoms"):
        question = "Have you noticed anything that makes the symptoms better or worse?"
        return ("symptom_triggers", format_question(question, is_guardian))
    
    if "previous_episodes" not in asked_questions and patient_info.get("symptoms"):
        question = "Have you experienced similar symptoms before?"
        return ("previous_episodes", format_question(question, is_guardian))
    
    if "fever_present" not in asked_questions and "fever" not in patient_info.get("symptoms", []):
        question = "Do you have a fever? If yes, what is your temperature?"
        return ("fever_present", format_question(question, is_guardian))
    
    if "eating_drinking" not in asked_questions:
        question = "Are you able to eat and drink normally?"
        return ("eating_drinking", format_question(question, is_guardian))
    
    if "sleep_patterns" not in asked_questions:
        question = "How have your sleep patterns been affected?"
        return ("sleep_patterns", format_question(question, is_guardian))
    
    if "stress_level" not in asked_questions:
        question = "On a scale of 1-10, how would you rate your current stress level?"
        return ("stress_level", format_question(question, is_guardian))
    
    return None, None

def validate_age(age_str):
    try:
        age = int(age_str)
        if age < 0 or age > 120:
            return False, "The age seems unusual. Please confirm the correct age."
        if age < 1:
            return False, "For infants under 1 year, please specify age in months"
        return True, None
    except:
        if "month" in age_str.lower():
            return True, None
        return False, "Please provide age as a number"

def validate_duration(duration_str):
    duration_lower = duration_str.lower()
    valid_units = ['hour', 'day', 'week', 'month', 'year', 'minute']
    has_valid_unit = any(unit in duration_lower for unit in valid_units)
    
    if not has_valid_unit:
        return False, "Please specify duration with time units"
    
    numbers = re.findall(r'\d+', duration_str)
    if not numbers:
        return False, "Please include how long"
    
    return True, None

def display_booking_form(doctor):
    st.markdown("---")
    st.markdown(f"## Book Appointment with Dr. {doctor['name']}")
    
    st.info(f"**{doctor['qualification']}** | **Specialty:** {doctor['specialization']}")
    st.write(f"**Available Time Slots:** {', '.join(doctor['time_slots'])}")
    
    with st.form(key=f"booking_form_{doctor['name']}"):
        st.markdown("### Patient Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            patient_name = st.text_input("Full Name *", placeholder="John Doe")
            patient_age = st.number_input("Age *", min_value=0, max_value=120, step=1, value=30)
            patient_gender = st.selectbox("Gender *", ["Select", "Male", "Female", "Other"])
        
        with col2:
            patient_phone = st.text_input("Phone Number *", placeholder="1234567890", max_chars=10)
            patient_email = st.text_input("Email", placeholder="johndoe@example.com")
            patient_id = st.text_input("Patient ID (if existing)", placeholder="Optional")
        
        st.markdown("### Appointment Details")
        
        col3, col4 = st.columns(2)
        
        with col3:
            today = datetime.now()
            min_date = today + timedelta(days=1)
            max_date = today + timedelta(days=30)
            
            preferred_date = st.date_input(
                "Preferred Date *",
                min_value=min_date,
                max_value=max_date,
                value=min_date,
                help="Select your preferred appointment date"
            )
            
            preferred_time = st.selectbox("Preferred Time Slot *", ["Select Time"] + doctor['time_slots'])
        
        with col4:
            appointment_type = st.selectbox(
                "Appointment Type *", 
                ["Select", "First Visit", "Follow-up", "Emergency Consultation", "Routine Checkup", "Second Opinion"]
            )
            
            urgency = st.selectbox("Urgency Level", ["Normal", "Urgent", "Emergency"])
        
        st.markdown("### Medical Information")
        default_symptoms = ""
        if hasattr(st.session_state, 'patient_info'):
            symptoms_list = st.session_state.patient_info.get('symptoms', [])
            if symptoms_list:
                default_symptoms = ", ".join(symptoms_list)
        
        reason_for_visit = st.text_area(
            "Reason for Visit / Chief Complaint *", 
            value=default_symptoms,
            placeholder="Brief description of symptoms or reason for consultation",
            height=100
        )
        
        medical_history = st.text_area(
            "Relevant Medical History",
            placeholder="Any chronic conditions, previous surgeries, allergies, current medications",
            height=80
        )
        
        st.markdown("### Additional Information")
        
        col5, col6 = st.columns(2)
        
        with col5:
            insurance_provider = st.text_input("Insurance Provider", placeholder="e.g., Blue Cross, Aetna")
            insurance_id = st.text_input("Insurance ID", placeholder="Policy number")
        
        with col6:
            preferred_language = st.selectbox("Preferred Language", ["English", "Hindi", "Spanish", "Other"])
            special_needs = st.text_input("Special Needs/Accessibility", placeholder="Wheelchair access, interpreter, etc.")
        
        additional_notes = st.text_area(
            "Additional Notes",
            placeholder="Any other information the doctor should know",
            height=60
        )
        consent = st.checkbox("I confirm that the information provided is accurate and I consent to the appointment booking *")
        
        st.markdown("---")
        
        col_submit, col_cancel = st.columns([1, 1])
        
        with col_submit:
            submit_button = st.form_submit_button("Confirm Booking", use_container_width=True, type="primary")
        
        with col_cancel:
            cancel_button = st.form_submit_button("Cancel", use_container_width=True)
        
        if submit_button:
            errors = []
            
            if not patient_name or len(patient_name.strip()) < 2:
                errors.append("Please enter a valid full name")
            
            if patient_age <= 0:
                errors.append("Please enter a valid age")
            
            if patient_gender == "Select":
                errors.append("Please select gender")
            
            if not patient_phone or len(patient_phone) != 10 or not patient_phone.isdigit():
                errors.append("Please enter a valid 10-digit phone number")
            if preferred_time == "Select Time":
                errors.append("Please select a preferred time slot")
            
            if appointment_type == "Select":
                errors.append("Please select appointment type")
            
            if not reason_for_visit or len(reason_for_visit.strip()) < 5:
                errors.append("Please provide a reason for visit")
            
            if not consent:
                errors.append("Please confirm consent to book appointment")
            
            if errors:
                st.error("### Please fix the following errors:")
                for error in errors:
                    st.error(error)
            else:
                booking_data = {
                    "booking_id": f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "booking_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "doctor_name": doctor['name'],
                    "doctor_qualification": doctor['qualification'],
                    "specialization": doctor['specialization'],
                    "patient_name": patient_name,
                    "patient_age": patient_age,
                    "patient_gender": patient_gender,
                    "patient_phone": patient_phone,
                    "patient_email": patient_email,
                    "patient_id": patient_id if patient_id else "New Patient",
                    "preferred_date": preferred_date.strftime("%Y-%m-%d"),
                    "preferred_time": preferred_time,
                    "appointment_type": appointment_type,
                    "urgency": urgency,
                    "reason_for_visit": reason_for_visit,
                    "medical_history": medical_history,
                    "insurance_provider": insurance_provider,
                    "insurance_id": insurance_id,
                    "preferred_language": preferred_language,
                    "special_needs": special_needs,
                    "additional_notes": additional_notes
                }
                if 'bookings' not in st.session_state:
                    st.session_state.bookings = []
                st.session_state.bookings.append(booking_data)
                st.success("### Appointment Booking Request Submitted Successfully!")
                
                st.markdown("---")
                st.markdown("### Booking Confirmation")
                
                conf_col1, conf_col2 = st.columns(2)
                
                with conf_col1:
                    st.write(f"**Booking ID:** {booking_data['booking_id']}")
                    st.write(f"**Patient:** {patient_name}")
                    st.write(f"**Age/Gender:** {patient_age} years / {patient_gender}")
                    st.write(f"**Phone:** {patient_phone}")
                    if patient_email:
                        st.write(f"**Email:** {patient_email}")
                
                with conf_col2:
                    st.write(f"**Doctor:** Dr. {doctor['name']}")
                    st.write(f"**Specialty:** {doctor['specialization']}")
                    st.write(f"**Date:** {preferred_date}")
                    st.write(f"**Time:** {preferred_time}")
                    st.write(f"**Type:** {appointment_type}")
                
                st.markdown("---")
                st.info(f"""
                ### Next Steps:
                
                1. **Confirmation Call**: You will receive a confirmation call/SMS at **{patient_phone}** within 2 hours
                2. **Appointment Details**: Check your email{f' ({patient_email})' if patient_email else ''} for detailed appointment information
                3. **Arrival Time**: Please arrive **15 minutes before** your scheduled appointment
                4. **Documents to Bring**:
                   - Valid ID proof
                   - Insurance card (if applicable)
                   - Previous medical records (if any)
                   - List of current medications
                
                **Emergency Contact:** 9880393380  
                **For Queries:** Call our helpline during business hours
                
                **Important:** This is a booking request. Final confirmation will be sent after verification.
                """)
                
                if 'selected_doctor_for_booking' in st.session_state:
                    del st.session_state.selected_doctor_for_booking
        
        if cancel_button:
            if 'selected_doctor_for_booking' in st.session_state:
                del st.session_state.selected_doctor_for_booking
            st.rerun()

def display_assessment(patient_info, score):
    st.markdown("---")
    st.subheader("ASSESSMENT SUMMARY")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Patient Information:**")
        st.write(f"**Age:** {patient_info.get('age', 'Not specified')}")
        st.write(f"**Gender:** {patient_info.get('gender', 'Not specified')}")
        st.write(f"**Symptoms:** {', '.join(patient_info.get('symptoms', [])) or 'None reported'}")
        st.write(f"**Duration:** {patient_info.get('duration', 'Not specified')}")
        st.write(f"**Severity:** {', '.join(patient_info.get('modifiers', [])) or 'Not specified'}")
        
        if patient_info.get("pain_score"):
            st.write(f"**Pain Level:** {patient_info.get('pain_score')}/10")
    
    with col2:
        st.markdown("**Medical Background:**")
        st.write(f"**Medical History:** {', '.join(patient_info.get('past_medical_history', [])) or 'None reported'}")
        
        habits_data = patient_info.get("habits", {})
        risk_factors = []
        if habits_data.get("smoking"):
            details = habits_data.get("smoking_details", {})
            risk_factors.append(f"Smoking ({details.get('years', '?')} years)")
        if habits_data.get("vaping"):
            risk_factors.append("Vaping")
        if habits_data.get("alcohol"):
            details = habits_data.get("alcohol_details", {})
            risk_factors.append(f"Alcohol ({details.get('drinks_per_week', '?')} drinks/week)")
        if habits_data.get("drug_use"):
            risk_factors.append("Substance use")
        
        if risk_factors:
            st.write(f"**Risk Factors:** {', '.join(risk_factors)}")
    st.markdown("---")
    if score >= 20:
        st.error("**PRIORITY: IMMEDIATE - CALL 911 OR GO TO ER IMMEDIATELY!**")
        st.error("These symptoms require emergency medical attention.")
    elif score >= 12:
        st.warning("**PRIORITY: URGENT - Should be seen within 2-4 hours**")
        st.warning("Please seek urgent care or emergency services.")
    elif score >= 6:
        st.info("**PRIORITY: LESS URGENT - Should be seen within 24 hours**")
        st.info("Schedule an appointment with a doctor today.")
    else:
        st.success("**PRIORITY: NON-URGENT - Routine appointment recommended**")
        st.success("A regular appointment with a primary care doctor can be scheduled.")
    st.markdown("---")
    st.markdown("### Possible Diagnoses")
    st.caption("*These are potential conditions based on reported symptoms. Only a healthcare provider can provide an accurate diagnosis.*")
    
    diagnoses = get_possible_diagnoses(patient_info)
    for i, diagnosis in enumerate(diagnoses, 1):
        urgency_color = {
            "EMERGENCY": "[CRITICAL]",
            "URGENT": "[URGENT]",
            "LESS URGENT": "[MODERATE]",
            "NON-URGENT": "[ROUTINE]"
        }
        color = urgency_color.get(diagnosis["urgency"], "[UNKNOWN]")
        
        with st.expander(f"{color} **{i}. {diagnosis['condition']}**"):
            st.write(f"**Reasoning:** {diagnosis['reasoning']}")
            st.write(f"**Urgency Level:** {diagnosis['urgency']}")
    st.markdown("---")
    specialties = doc(patient_info)
    st.markdown("### Recommended Medical Specialties")
    
    for i, specialty in enumerate(specialties, 1):
        reasoning = get_specialty_reasoning(
            specialty, 
            patient_info.get("symptoms", []),
            patient_info.get("past_medical_history", []),
            patient_info.get("habits", {})
        )
        st.markdown(f"**{i}. {specialty}**")
        st.write(f"   *{reasoning}*")
        st.write("")
    st.markdown("---")
    st.markdown("### Available Doctors - Click to Book Appointment")
    all_doctors = doctors()
    
    if all_doctors:
        for specialty in specialties:
            matching_doctors = [d for d in all_doctors if d['specialization'] == specialty]
            if matching_doctors:
                st.markdown(f"#### {specialty}")
                for doctor in matching_doctors:
                    col_doc, col_time, col_book = st.columns([3, 2, 1.5])
                    
                    with col_doc:
                        st.write(f"**Dr. {doctor['name']}**")
                        st.caption(doctor['qualification'])
                    
                    with col_time:
                        st.write(f"Available: {doctor['time_slots'][0]}")
                        if len(doctor['time_slots']) > 1:
                            st.caption(f"& {len(doctor['time_slots'])-1} more slot(s)")
                    
                    with col_book:
                        if st.button(
                            "Book Now", 
                            key=f"book_{doctor['name']}_{specialty}",
                            use_container_width=True,
                            type="primary"
                        ):
                            st.session_state.selected_doctor_for_booking = doctor
                            st.rerun()
                
                st.markdown("")
        all_shown = any([d for d in all_doctors if d['specialization'] in specialties])
        if not all_shown:
            st.markdown("#### General Medicine")
            general_docs = [d for d in all_doctors if d['specialization'] == 'General Medicine']
            for doctor in general_docs:
                col_doc, col_time, col_book = st.columns([3, 2, 1.5])
                
                with col_doc:
                    st.write(f"**Dr. {doctor['name']}**")
                    st.caption(doctor['qualification'])
                
                with col_time:
                    st.write(f"Available: {doctor['time_slots'][0]}")
                    if len(doctor['time_slots']) > 1:
                        st.caption(f"& {len(doctor['time_slots'])-1} more slot(s)")
                
                with col_book:
                    if st.button(
                        "Book Now", 
                        key=f"book_{doctor['name']}_general",
                        use_container_width=True,
                        type="primary"
                    ):
                        st.session_state.selected_doctor_for_booking = doctor
                        st.rerun()
    else:
        st.info("Doctor information not available. Please contact reception for appointments.")
    if hasattr(st.session_state, 'selected_doctor_for_booking') and st.session_state.selected_doctor_for_booking:
        display_booking_form(st.session_state.selected_doctor_for_booking)
def main():
    st.set_page_config(page_title="Medemi - Medical Triage Assistant", page_icon="⚕️", layout="wide")
    st.markdown("""
    <style>
    .stApp {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0a0a0a !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #FFFFFF !important;
    }
    
    h1 {
        font-weight: 800 !important;
        letter-spacing: -1px !important;
    }
    
    h2 {
        font-weight: 700 !important;
    }
    
    h3 {
        font-weight: 600 !important;
    }
    
    .stChatMessage {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stChatMessageContent"] {
        color: #FFFFFF !important;
    }
    
    .stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 5px !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #666666 !important;
        box-shadow: 0 0 0 1px #666666 !important;
    }
    
    .stChatInputContainer {
        background-color: #000000 !important;
    }
    
    .stChatInputContainer input {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
    }
    
    .stButton button {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton button:hover {
        background-color: #2a2a2a !important;
        border-color: #666666 !important;
        transform: translateY(-2px) !important;
    }
    
    .stButton button[kind="primary"] {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .stButton button[kind="primary"]:hover {
        background-color: #CC0000 !important;
    }
    
    .stFormSubmitButton button {
        font-weight: 600 !important;
    }
    
    .stDateInput {
        background-color: #1a1a1a !important;
    }
    
    .stDateInput input {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
    }
    
    [data-baseweb="calendar"] {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar"] * {
        color: #FFFFFF !important;
    }
    
    [data-baseweb="calendar-header"] {
        background-color: #0a0a0a !important;
    }
    
    [data-baseweb="day"] {
        color: #FFFFFF !important;
    }
    
    [data-baseweb="day"]:hover {
        background-color: #2a2a2a !important;
    }
    
    [aria-selected="true"] {
        background-color: #FF0000 !important;
        color: #FFFFFF !important;
    }
    
    [data-baseweb="day"][aria-label*="today"] {
        border: 2px solid #FF0000 !important;
    }
    
    .stAlert {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        color: #FFFFFF !important;
    }
    
    .stSuccess {
        background-color: #0a3d0a !important;
        border-color: #0f5a0f !important;
    }
    
    .stInfo {
        background-color: #0a1f3d !important;
        border-color: #0f2f5a !important;
    }
    
    .stWarning {
        background-color: #3d2a0a !important;
        border-color: #5a3f0f !important;
    }
    
    .stError {
        background-color: #3d0a0a !important;
        border-color: #5a0f0f !important;
    }
    
    .streamlit-expanderHeader {
        background-color: #1a1a1a !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderContent {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-top: none !important;
    }
    
    [data-testid="column"] {
        background-color: transparent !important;
    }
    
    .stMarkdown {
        color: #FFFFFF !important;
    }
    
    .stCaption {
        color: #999999 !important;
    }
    
    hr {
        border-color: #333333 !important;
    }
    
    .stSpinner > div {
        border-top-color: #FFFFFF !important;
    }
    
    .stForm {
        background-color: #0a0a0a !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }
    
    .stCheckbox {
        color: #FFFFFF !important;
    }
    
    [data-baseweb="select"] {
        background-color: #1a1a1a !important;
    }
    
    [data-baseweb="select"] * {
        color: #FFFFFF !important;
        background-color: #1a1a1a !important;
    }
    
    [data-baseweb="calendar"] {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
    }
    
    [data-testid="stMetric"] {
        background-color: #1a1a1a !important;
        border: 1px solid #333333 !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0a0a0a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #333333;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #555555;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Medemi - Medical Triage Assistant")
    st.markdown("Get preliminary medical assessment and doctor recommendations")
    st.caption("This is not a substitute for professional medical advice")
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.stage = "initial"
        st.session_state.patient_info = {"habits": {}}
        st.session_state.asked_questions = set()
        st.session_state.conversation_history = []
        st.session_state.initial_text = ""
        st.session_state.validation_errors = []
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hello! This is a medical triage assistant. Please describe the patient's symptoms and any relevant medical history."
        })
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if prompt := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        if st.session_state.stage == "initial":
            with st.chat_message("assistant"):
                with st.spinner("Analyzing the information..."):
                    st.session_state.initial_text = prompt
                    response = extract_with_llm(prompt)
                    
                    try:
                        start = response.find('{')
                        end = response.rfind('}') + 1
                        extracted = json.loads(response[start:end])
                        st.session_state.patient_info.update(extracted)
                    except:
                        pass
                    
                    st.session_state.stage = "questions"
                    
                    key, question = get_follow_up_question(st.session_state.patient_info, st.session_state.asked_questions)
                    if question:
                        st.markdown(question)
                        st.session_state.messages.append({"role": "assistant", "content": question})
                        st.session_state.current_question_key = key
                    else:
                        st.session_state.stage = "complete"
                        st.rerun()
        
        elif st.session_state.stage == "questions":
            current_key = st.session_state.current_question_key
            st.session_state.asked_questions.add(current_key)
            validation_passed = True
            if current_key == "age":
                is_valid, error_msg = validate_age(prompt)
                if not is_valid:
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.session_state.asked_questions.remove(current_key)
                    validation_passed = False
            
            elif current_key == "duration":
                is_valid, error_msg = validate_duration(prompt)
                if not is_valid:
                    with st.chat_message("assistant"):
                        st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.session_state.asked_questions.remove(current_key)
                    validation_passed = False
            
            if validation_passed:
                last_question = [msg for msg in st.session_state.messages if msg["role"] == "assistant"][-1]["content"]
                st.session_state.conversation_history.append(f"Q: {last_question}\nA: {prompt}")
                if current_key == "age":
                    try:
                        st.session_state.patient_info["age"] = str(int(prompt))
                    except:
                        st.session_state.patient_info["age"] = prompt
                
                elif current_key == "gender":
                    st.session_state.patient_info["gender"] = prompt.lower()
                
                elif current_key == "duration":
                    st.session_state.patient_info["duration"] = prompt
                
                elif current_key == "modifiers":
                    if "modifiers" not in st.session_state.patient_info:
                        st.session_state.patient_info["modifiers"] = []
                    for mod in mods:
                        if mod in prompt.lower():
                            if mod not in st.session_state.patient_info["modifiers"]:
                                st.session_state.patient_info["modifiers"].append(mod)
                
                elif current_key == "past_medical_history":
                    if "past_medical_history" not in st.session_state.patient_info:
                        st.session_state.patient_info["past_medical_history"] = []
                    for condition in past:
                        if condition.lower() in prompt.lower():
                            if condition not in st.session_state.patient_info["past_medical_history"]:
                                st.session_state.patient_info["past_medical_history"].append(condition)
                
                elif current_key == "pain_scale":
                    try:
                        pain_num = int(re.findall(r'\d+', prompt)[0])
                        st.session_state.patient_info["pain_score"] = min(10, max(0, pain_num))
                    except:
                        st.session_state.patient_info["pain_score"] = calculate_pain_score(prompt)
                
                elif current_key == "pregnancy_possibility":
                    st.session_state.patient_info["pregnancy_possible"] = prompt.lower() in ["yes", "y", "yeah", "yep", "maybe", "possibly"]
                
                else:
                    st.session_state.patient_info[current_key] = prompt
                key, question = get_follow_up_question(st.session_state.patient_info, st.session_state.asked_questions)
                
                if question:
                    with st.chat_message("assistant"):
                        st.markdown(question)
                    st.session_state.messages.append({"role": "assistant", "content": question})
                    st.session_state.current_question_key = key
                else:
                    st.session_state.stage = "complete"
                    
                    with st.chat_message("assistant"):
                        with st.spinner("Processing complete information..."):
                            if st.session_state.conversation_history:
                                full_history = "\n".join(st.session_state.conversation_history)
                                response = extract_with_llm(st.session_state.initial_text, full_history)
                                try:
                                    start = response.find('{')
                                    end = response.rfind('}') + 1
                                    extracted = json.loads(response[start:end])
                                    for key, value in extracted.items():
                                        if value and key not in ["habits"]:
                                            if isinstance(value, list) and key in st.session_state.patient_info:
                                                existing = st.session_state.patient_info[key]
                                                if isinstance(existing, list):
                                                    combined = list(set(existing + value))
                                                    st.session_state.patient_info[key] = combined
                                                else:
                                                    st.session_state.patient_info[key] = value
                                            else:
                                                st.session_state.patient_info[key] = value
                                except Exception as e:
                                    print(f"Extraction error: {e}")
                            score, _ = triage(json.dumps(st.session_state.patient_info))
                            st.session_state.triage_score = score
                            
                            st.markdown("### Assessment Complete!")
                            st.markdown("**Your personalized medical assessment is ready below.**")
                            st.markdown("Scroll down to view your results and book an appointment with recommended specialists.")
                    
                    st.session_state.stage = "show_assessment"
                    st.rerun()
    if st.session_state.stage in ["show_assessment", "complete"] and st.session_state.patient_info.get("symptoms"):
        display_assessment(st.session_state.patient_info, st.session_state.get('triage_score', 5))
    with st.sidebar:
        st.header("About")
        st.info("This is a preliminary medical triage assistant.")
        
        st.markdown("---")
        st.markdown("### Emergency Numbers")
        st.error("**Emergency: 112**")
        st.markdown("**Helpline: 9880393380**")
        
        if st.button("Start New Consultation"):
            bookings_backup = st.session_state.get('bookings', [])
            st.session_state.clear()
            st.session_state.bookings = bookings_backup
            st.rerun()
        if 'bookings' in st.session_state and st.session_state.bookings:
            st.markdown("---")
            st.markdown(f"### Booking History ({len(st.session_state.bookings)})")
            for booking in st.session_state.bookings[-3:]:
                with st.expander(f"{booking['booking_id']} - Dr. {booking['doctor_name']}"):
                    st.write(f"**Patient:** {booking['patient_name']}")
                    st.write(f"**Date:** {booking['preferred_date']}")
                    st.write(f"**Time:** {booking['preferred_time']}")
        
        st.markdown("---")
        st.caption("v3.0.0 - Medemi Medical Triage System")

if __name__ == "__main__":
    main()
