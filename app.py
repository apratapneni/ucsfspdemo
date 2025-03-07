from flask import Flask, request, jsonify, render_template, render_template_string
import time
import json
from openai import OpenAI
import os

api_key = os.getenv("DEEPSEEK_API")
if api_key is None:
    raise Exception("Please set the DEEPSEEK_API environment variable.")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

app = Flask(__name__)

def query_system(system_prompt, prompt, max_tokens=256):
    '''
    Literally just a helper function that queries GPT
    '''
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}]

    return client.chat.completions.create(
          model="deepseek-reasoner",
          messages=messages,
          max_tokens=max_tokens,
          temperature=0.8,
          top_p=0.95
        )['choices'][0]['message']['content']

def query(prompt, max_tokens=256):
    '''
    Literally just a helper function that queries GPT
    '''
    messages = [{"role": "user", "content": prompt}]

    return client.chat.completions.create(
          model="deepseek-reasoner",
          messages=messages,
          max_tokens=max_tokens,
          temperature=0.8,
          top_p=0.95
        )['choices'][0]['message']['content']

def chat(input_messages, system_prompt, max_tokens=256):
    '''
    Literally just a helper function that queries GPT
    '''
    messages = [{"role": "system", "content": system_prompt}]

    for i, message in enumerate(input_messages):
        if i % 2 == 0:
            messages.append({"role": "user", "content": message})
        else:
            messages.append({"role": "assistant", "content": message})

    return client.chat.completions.create(
          model="deepseek-reasoner",
          messages=messages,
          max_tokens=max_tokens,
          temperature=0.8,
          top_p=0.95
        )['choices'][0]['message']['content']

#load system prompt from system_prompt.txt
with open('SP_system_prompt.txt', 'r', encoding='utf-8') as f:
    base_system_prompt = f.read()

def query_learning_objectives(clinical_vignette):
    prompt = """You are a medical school professor. Given a clinical case vignette, you output a list of learning objectives, separated by newlines, that a medical student would be expected to fulfill regarding the case throughout the treatment and conversation with a patient. The learning objectives should be a mixture of objectives that test general clinical skill/knowledge, in addition to skills that test clinical skills/knowledge specific to the case.

A grader will later need to evaluate whether the student fulfilled these objectives based on a transcript between the student and the patient, in addition to the labs the student orders. Ensure that the generated learning objectives can be evaluated from these.
""".strip()
    
    return query_system(prompt, clinical_vignette).strip()

def query_labs(order, clinical_vignette, vitals_and_labs):
    '''
    This is where you would query your own database for vitals and labs
    '''
    prompt = f"""Given the following clinical vignette and labs, report the most likely result of the following order.
Clinical Vignette: {clinical_vignette}
Vitals and Labs: {vitals_and_labs}
Order: {order}
Report strictly the result of the lab, and report it as fact. Do not suggest any further labs or add any additional information.
If the lab information is not provided above, fabricate a reasonable result given the clinical vignette and report it as fact.
""".strip()
    
    return query(prompt).strip().replace("\n", "<br>")

@app.route('/api/professor-response', methods=['POST'])
def professor_response():
    #save request.json to log file, with timestamp and IP address
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + ' ' + request.remote_addr + ' ' + json.dumps(request.json) + '\n')
    
    chat_history = request.json.get('chat_history')[:-1]
    system_prompt = base_system_prompt.replace("{clinical_vignette}", request.json.get('vignette'))
    system_prompt = system_prompt.replace("{vitals_and_labs}", request.json.get('labs'))

    #parse chat history
    messages = []
    for message in chat_history:
        messages.append(': '.join(message.split(': ')[1:]).replace('<br>', '\n').strip())
    
    if messages[-1][0] == "*" and messages[-1][-1] == "*":
        return jsonify(professor_response=query_labs(messages[-1][1:-1], request.json.get('vignette'), request.json.get('labs')))

    return jsonify(professor_response=chat(messages, system_prompt).strip())

@app.route('/api/grading', methods=['POST'])
def grade():
    #save request.json to log file, with timestamp and IP address
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + ' ' + request.remote_addr + ' ' + json.dumps(request.json) + '\n')
    
    chat_history = request.json.get('chat_history')[:-1]
    system_prompt =  """You are a grader at a medical school. The user will input an entire chat transcript to you. Given the following clinical vignette and learning objectives listed below, for each objective you will first determine if the student met the objective. If not, you will provide an explanation as to why the student did not meet the objective.

Example output:
✅ <b>Learing Objective: The student should order a CBC.</b>
❌ <b>Learing Objective: The student should order a BMP;</b> <i> The student did not order a BMP. The student should have ordered a BMP because the patient had a history of diabetes. </i>

The following are the clinical vignette and learning objectives:

Clinical Vignette: 
{clinical_vignette}

Learning Objectives: 
{learning_objectives}
""".strip()
    
    system_prompt = system_prompt.replace("{clinical_vignette}", request.json.get('vignette'))
    system_prompt = system_prompt.replace("{learning_objectives}", request.json.get('learning_objectives'))

    #parse chat history
    message_string = ""
    for i, message in enumerate(chat_history):
        if i % 2 == 0:
            message_string += "Student: " + ': '.join(message.split(': ')[1:]).replace('<br>', '\n').strip() + "\n"
        else:
            message_string += "Patient: " + ': '.join(message.split(': ')[1:]).replace('<br>', '\n').strip() + "\n"

    return jsonify(grading=query_system(system_prompt, message_string, 2048).strip().replace("\n", "<br>"))

# Set random_case.html as the default route
@app.route('/', methods=['GET', 'POST'])
@app.route('/random_case.html', methods=['GET', 'POST'])
def random_case():
    if request.method == 'GET':
        return render_template('random_case.html')
    else:
        case_description = request.form['input_data']
        instructions = request.form['instructions']

        #log
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + ' ' + request.remote_addr + ' ' + case_description + ' ' + instructions + '\n')
        
        if instructions == "":
            instructions = "No additional instructions."

        system_prompt = f"""You are a bot that creates clinical vignettes based on a simple case description and any additional instructions. Your goal is to create a clinical vignette that is as realistic as possible.

Example:
Case description: A 65-year-old woman with pneumonia.

Additional instructions: No additional instructions.

Output:
Ms. Smith, a 65-year-old woman, presents to the emergency department (ED) with a 3-day history of worsening shortness of breath, productive cough with yellowish sputum, and fever. She has a past medical history of hypertension, type 2 diabetes mellitus, and chronic obstructive pulmonary disease (COPD). She is a former smoker, having quit 10 years ago, and denies any recent travel, sick contacts, or exposure to tuberculosis. On further questioning, she reports feeling increasingly fatigued over the past week and has been experiencing night sweats.
""".strip()
        vignette = query_system(system_prompt, f"Case description: {case_description}\nAdditional instructions: {instructions}\n", max_tokens=256).strip()

        system_prompt = f"""You are a bot that creates realistic labs and findings based on a clinical vignette. Your goal is to create labs and findings that are as realistic as possible.

Example:
Vignette: Ms. Smith, a 65-year-old woman, presents to the emergency department (ED) with a 3-day history of worsening shortness of breath, productive cough with yellowish sputum, and fever. She has a past medical history of hypertension, type 2 diabetes mellitus, and chronic obstructive pulmonary disease (COPD). She is a former smoker, having quit 10 years ago, and denies any recent travel, sick contacts, or exposure to tuberculosis. On further questioning, she reports feeling increasingly fatigued over the past week and has been experiencing night sweats.

Output:
Temperature: 38.5°C (101.3°F)\nBlood Pressure: 145/90 mmHg\nHeart Rate: 110 bpm\nRespiratory Rate: 22 breaths/min\nOxygen Saturation: 92% on room air\nComplete Blood Count (CBC):\n- WBC: 15,000 cells/µL (normal range: 4,500-11,000 cells/µL)\n- Hemoglobin: 12 g/dL (normal range: 12-16 g/dL)\n- Platelets: 300,000 cells/µL (normal range: 150,000-450,000 cells/µL)\nBlood Chemistry:\n- Sodium: 140 mmol/L (normal range: 135-145 mmol/L)\n- Potassium: 4.0 mmol/L (normal range: 3.5-5.0 mmol/L)\n- Creatinine: 1.0 mg/dL (normal range: 0.6-1.2 mg/dL)\n- Blood Urea Nitrogen (BUN): 20 mg/dL (normal range: 6-20 mg/dL)\n- Glucose: 180 mg/dL (normal range: 70-110 mg/dL)\nChest X-Ray: Right middle lobe consolidation consistent with pneumonia.
""".strip()
        labs = query_system(system_prompt, f"Vignette: {vignette}\n", max_tokens=256).strip()

        learning_objectives = query_learning_objectives(clinical_vignette=vignette)

        #open random_case.html
        with open('templates/case_template.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        #replace {vignette} and {labs} with generated vignette and labs
        html = html.replace("{vignette_visible}", (vignette + "\n\n" + labs).replace("\n", "<br>"))
        html = html.replace("{vignette}", vignette.replace("\n", "\\n"))
        html = html.replace("{findings}", labs.replace("\n", "\\n"))
        html = html.replace("{learning_objectives}", learning_objectives.replace("\n", "\\n"))

    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)