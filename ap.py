import ollama
import json
import os

symptoms=["fever","cough","headache","nausea","fatigue","dizziness","shortness of breath","chest pain","abdominal pain","diarrhea","vomiting","sore throat","runny nose","muscle aches","joint pain","rash","swelling","weight loss","weight gain","night sweats","chills","edema","orthopnea","reduced urine output"]
mods=["mild","moderate","severe","intermittent","constant","sudden onset","gradual onset","worsening","improving","persistent","recurring"]
past=["diabetes","hypertension","asthma","heart disease","cancer","stroke","kidney disease","liver disease","COPD","arthritis","depression","anxiety","thyroid disorder","autoimmune disease","allergies","previous surgeries","cardiomyopathy"]

def triage(txt):
    score=0
    try:
        s=txt.find('{')
        e=txt.rfind('}')+1
        data=json.loads(txt[s:e])
    except:
        return 0, {}
    sc={"fever":2,"cough":1,"shortness of breath":3,"chest pain":3,"abdominal pain":2,"diarrhea":1,"vomiting":1,"sore throat":1,"runny nose":1,"muscle aches":1,"joint pain":1,"rash":2,"swelling":2,"weight loss":2,"weight gain":1,"night sweats":2,"chills":1,"edema":2,"orthopnea":3,"reduced urine output":3,"dizziness":2,"nausea":1}
    for s in data.get("symptoms",[]):
        if s in sc:
            score+=sc[s]
    ms={"mild":1,"moderate":2,"severe":3,"intermittent":1,"constant":2,"sudden onset":3,"gradual onset":1,"worsening":2,"improving":-1,"persistent":2,"recurring":1}
    for m in data.get("modifiers",[]):
        if m in ms:
            score+=ms[m]
    age=data.get("age","")
    if age:
        try:
            a=int(age)
            if a>=60:
                score*=1.5+(a-60)/10
        except:
            pass
    ps={"diabetes":2,"hypertension":2,"asthma":2,"heart disease":3,"cancer":3,"stroke":3,"kidney disease":3,"liver disease":3,"COPD":3,"arthritis":1,"depression":1,"anxiety":1,"thyroid disorder":1,"autoimmune disease":2,"allergies":1,"previous surgeries":1,"cardiomyopathy":3}
    for p in data.get("past medical history",[]):
        if p in ps:
            score+=ps[p]
    return round(score,1), data

def doc(score):
    speciality={
        "Cardiology":["chest pain","shortness of breath","orthopnea","edema"],
        "Pulmonology":["shortness of breath","cough","orthopnea"],
        "Gastroenterology":["abdominal pain","diarrhea","vomiting"],
        "Neurology":["headache","dizziness"],
        "Infectious Disease":["fever","chills","night sweats"],
        "Rheumatology":["joint pain","muscle aches","rash"],
        "Endocrinology":["weight loss","weight gain"],
        "Nephrology":["reduced urine output","edema"],
        "Hematology":["weight loss","night sweats"],
        "Oncology":["weight loss","night sweats","chills"],
        "Psychiatry":["depression","anxiety"],
        "ENT":["sore throat","runny nose"],
        "Pediatrics":["fever","cough","vomiting","diarrhea"],
        "Dermatology":["rash","swelling"],
        "Orthopedics":["joint pain","muscle aches"],
        "Ophthalmology":["headache","dizziness"],
        "General Medicine":["fever","cough","headache","nausea","fatigue"]
    }
    matched = [s for s,syms in speciality.items() if any(sym in syms for sym in score.get("symptoms",[]))]
    return matched[0:3] if matched else ["General Medicine"]

def doctors():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, "doctors.json")
    with open(json_file, 'r') as f:
        data = json.load(f)
    return data['doctors']

def ask_follow_up_questions(initial_data):
    conversation_history = []
    patient_info = initial_data.copy()
    
    questions_to_ask = []
    
    if not patient_info.get("age"):
        questions_to_ask.append(("age", "What is your age?"))
    
    if not patient_info.get("gender"):
        questions_to_ask.append(("gender", "What is your gender? (male/female/other)"))
    
    if not patient_info.get("duration"):
        questions_to_ask.append(("duration", "How long have you been experiencing these symptoms?"))
    
    if not patient_info.get("modifiers") and patient_info.get("symptoms"):
        questions_to_ask.append(("modifiers", f"How would you describe the severity of your {patient_info['symptoms'][0] if patient_info['symptoms'] else 'symptoms'}? (mild/moderate/severe)"))
    
    if not patient_info.get("past_medical_history"):
        questions_to_ask.append(("past_medical_history", "Do you have any existing medical conditions? (e.g., diabetes, hypertension, asthma)"))
    
    symptoms = patient_info.get("symptoms", [])
    if "chest pain" in symptoms:
        questions_to_ask.append(("chest_pain_details", "Does the chest pain radiate to your arm, jaw, or back?"))
    if "fever" in symptoms:
        questions_to_ask.append(("fever_temp", "What is your temperature?"))
    if "headache" in symptoms:
        questions_to_ask.append(("headache_location", "Where is the headache located? Is it throbbing or constant?"))
    
    for key, question in questions_to_ask:
        print(f"\nBot: {question}")
        answer = input("You: ").strip()
        
        if answer:
            conversation_history.append(f"Q: {question}\nA: {answer}")
            
            if key == "age":
                try:
                    patient_info["age"] = str(int(answer))
                except:
                    patient_info["age"] = answer
            elif key == "gender":
                patient_info["gender"] = answer.lower()
            elif key == "duration":
                patient_info["duration"] = answer
            elif key == "modifiers":
                if answer.lower() in ["mild", "moderate", "severe"]:
                    if "modifiers" not in patient_info:
                        patient_info["modifiers"] = []
                    patient_info["modifiers"].append(answer.lower())
            elif key == "past_medical_history":
                for condition in past:
                    if condition.lower() in answer.lower():
                        if "past_medical_history" not in patient_info:
                            patient_info["past_medical_history"] = []
                        patient_info["past_medical_history"].append(condition)
    
    return patient_info, conversation_history

def extract_with_llm(text, conversation_history=""):
    full_context = text
    if conversation_history:
        full_context = f"{text}\n\nAdditional Information:\n{conversation_history}"
    
    prompt=f"""You are a medical information extraction system. Your task is to analyze patient text and extract structured data with high precision.

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
    
    res=ollama.generate(model="mistral:7b", prompt=prompt)
    return res['response']

def main():
    print("=" * 80)
    print("MEDICAL TRIAGE ASSISTANT")
    print("=" * 80)
    print("\nBot: Hello! I'm here to help assess your medical needs.")
    print("Bot: Please describe your symptoms and any relevant medical history.\n")
    
    txt=input("You: ")
    
    print("\nAnalyzing your information...\n")
    
    response = extract_with_llm(txt)
    
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        initial_data = json.loads(response[start:end])
    except:
        initial_data = {"symptoms": [], "modifiers": [], "past_medical_history": [], "duration": "", "age": "", "gender": ""}
    
    print("\nBot: Thank you. I'd like to ask a few follow-up questions to better understand your situation.\n")
    patient_info, conversation_history = ask_follow_up_questions(initial_data)
    
    if conversation_history:
        print("\nProcessing complete information...\n")
        full_history = "\n".join(conversation_history)
        response = extract_with_llm(txt, full_history)
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            patient_info = json.loads(response[start:end])
        except:
            pass
    
    s, extracted_data = triage(json.dumps(patient_info))
    
    print("\n" + "=" * 80)
    print("ASSESSMENT SUMMARY")
    print("=" * 80)
    
    print(f"\nExtracted Information:")
    print(f"   Symptoms: {', '.join(patient_info.get('symptoms', [])) or 'None reported'}")
    print(f"   Severity: {', '.join(patient_info.get('modifiers', [])) or 'Not specified'}")
    print(f"   Duration: {patient_info.get('duration', 'Not specified')}")
    print(f"   Age: {patient_info.get('age', 'Not specified')}")
    print(f"   Gender: {patient_info.get('gender', 'Not specified')}")
    print(f"   Medical History: {', '.join(patient_info.get('past_medical_history', [])) or 'None reported'}")
    
    print(f"\nTriage Score: {s}")
    
    if s>=20:
        print("PRIORITY: IMMEDIATE - Seek emergency care immediately!")
    elif s>=12:
        print("PRIORITY: URGENT - You should be seen within 2-4 hours")
    elif s>=6:
        print("PRIORITY: LESS URGENT - You should be seen within 24 hours")
    else:
        print("PRIORITY: NON-URGENT - Routine appointment recommended")
    
    specialties = doc(patient_info)
    print(f"\nRECOMMENDED SPECIALTIES:")
    for i, specialty in enumerate(specialties, 1):
        print(f"   {i}. {specialty}")
    
    print(f"\nAVAILABLE DOCTORS:")
    all_doctors = doctors()
    
    shown_doctors = 0
    for specialty in specialties:
        matching_doctors = [d for d in all_doctors if d['specialization'] == specialty]
        if matching_doctors:
            print(f"\n   {specialty}:")
            for d in matching_doctors[:2]:
                print(f"      - {d['name']}")
                print(f"        Available: {', '.join(d['time_slots'])}")
                shown_doctors += 1
    
    if shown_doctors == 0:
        print("   No matching specialists found. Showing general practitioners:")
        general_docs = [d for d in all_doctors if d['specialization'] == 'General Medicine'][:3]
        for d in general_docs:
            print(f"      - {d['name']}")
            print(f"        Available: {', '.join(d['time_slots'])}")
    
    print("\n" + "=" * 80)
    print("Bot: Would you like to book an appointment? (yes/no)")
    booking = input("You: ").strip().lower()
    
    if booking in ['yes', 'y']:
        print("\nBot: Great! Please call our reception at 1-800-MEDICAL to book.")
    else:
        print("\nBot: Take care! Feel free to return if your symptoms worsen.")
    
    print("\n" + "=" * 80)

if __name__=="__main__":
    main()