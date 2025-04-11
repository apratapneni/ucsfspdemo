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
app.config['TEMPLATES_AUTO_RELOAD'] = True

def query_system(system_prompt, prompt, max_tokens=256):
    '''
    Helper function that queries the LLM API
    '''
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}]

    try:
        response = client.chat.completions.create(
              model="deepseek-chat",
              messages=messages,
              max_tokens=max_tokens,
              temperature=0.8,
              top_p=0.95
            )
        # Access the content property correctly
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {str(e)}")
        raise e

def query(prompt, max_tokens=256):
    '''
    Helper function that queries GPT with a single prompt
    '''
    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = client.chat.completions.create(
              model="deepseek-chat",
              messages=messages,
              max_tokens=max_tokens,
              temperature=0.8,
              top_p=0.95
            )
        # Access the content property correctly
        return response.choices[0].message.content
    except Exception as e:
        print(f"API Error: {str(e)}")
        raise e

def chat(input_messages, system_prompt, max_tokens=256):
    '''
    Helper function that queries GPT with chat history
    '''
    messages = [{"role": "system", "content": system_prompt}]

    for i, message in enumerate(input_messages):
        if i % 2 == 0:
            messages.append({"role": "user", "content": message})
        else:
            messages.append({"role": "assistant", "content": message})
    
    try:
        response = client.chat.completions.create(
              model="deepseek-chat",
              messages=messages,
              max_tokens=max_tokens,
              temperature=0.8,
              top_p=0.95
            )
        # Access the content property correctly with dot notation
        return response.choices[0].message.content
    except Exception as e:
        print(f"Chat API Error: {str(e)}")
        raise e

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

# Route for the homepage (index.html)
@app.route('/')
def index():
    return render_template('index.html')

# Route for chat (chat.html)
@app.route('/chat')
def chat_page():
    # Pass any necessary parameters if needed.
    return render_template('chat.html')

# Route for feedback (feedback.html)
@app.route('/feedback.html')  # Match the URL in your chat.html
def feedback_page():
    return render_template('feedback.html')

@app.route('/feedback.html')
def feedback_html():
    return render_template('feedback.html')

@app.route('/api/professor-response', methods=['POST'])
def professor_response():
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + ' ' + request.remote_addr + ' ' + json.dumps(request.json) + '\n')
    
    chat_history = request.json.get('chat_history', [])[:-1]  # Get all but the latest message
    
    # If chat_history is empty, initialize it
    if not chat_history:
        chat_history = ["User: Hello"]
    
    system_prompt = base_system_prompt.replace("{clinical_vignette}", request.json.get('vignette', ''))
    system_prompt = system_prompt.replace("{vitals_and_labs}", request.json.get('labs', ''))

    #parse chat history
    messages = []
    for message in chat_history:
        try:
            parts = message.split(':', 1)
            if len(parts) > 1:
                messages.append(parts[1].replace('<br>', '\n').strip())
            else:
                messages.append(message.replace('<br>', '\n').strip())
        except Exception as e:
            app.logger.error(f"Error parsing message: {message}, {str(e)}")
            continue
    
    # Get the latest message from the request
    latest_message = request.json.get('chat_history', [])[-1]
    if latest_message:
        try:
            parts = latest_message.split(':', 1)
            if len(parts) > 1:
                latest_content = parts[1].replace('<br>', '\n').strip()
            else:
                latest_content = latest_message.replace('<br>', '\n').strip()
            
            messages.append(latest_content)
        except Exception as e:
            app.logger.error(f"Error parsing latest message: {latest_message}, {str(e)}")
    
    # Check if this is a lab order request (surrounded by asterisks)
    if messages and messages[-1].startswith('*') and messages[-1].endswith('*'):
        lab_order = messages[-1][1:-1]  # Remove the asterisks
        try:
            return jsonify(professor_response=query_labs(lab_order, request.json.get('vignette', ''), request.json.get('labs', '')))
        except Exception as e:
            app.logger.error(f"Error processing lab order: {str(e)}")
            return jsonify(professor_response="I'm sorry, there was an error processing your lab request."), 500
    
    # Regular chat response
    try:
        response = chat(messages, system_prompt).strip()
        return jsonify(professor_response=response)
    except Exception as e:
        app.logger.error(f"Error generating chat response: {str(e)}")
        return jsonify(professor_response="I'm sorry, there was an error generating a response."), 500

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

# Add this new route:
@app.route('/generate_case', methods=['POST'])
def generate_case():
    case_description = request.form['input_data']
    
    # Log
    with open('log.txt', 'a', encoding='utf-8') as f:
        f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + ' ' + request.remote_addr + ' ' + case_description + '\n')
    
    system_prompt = f"""You are a bot that creates clinical vignettes based on a simple case description. Your goal is to create a clinical vignette that is as realistic as possible.

Example:
Case description: A 65-year-old woman with pneumonia.

Output:
Ms. Smith, a 65-year-old woman, presents to the emergency department (ED) with a 3-day history of worsening shortness of breath, productive cough with yellowish sputum, and fever. She has a past medical history of hypertension, type 2 diabetes mellitus, and chronic obstructive pulmonary disease (COPD). She is a former smoker, having quit 10 years ago, and denies any recent travel, sick contacts, or exposure to tuberculosis. On further questioning, she reports feeling increasingly fatigued over the past week and has been experiencing night sweats.
""".strip()
    
    try:
        vignette = query_system(system_prompt, f"Case description: {case_description}", max_tokens=256).strip()

        system_prompt = f"""You are a bot that creates realistic labs and findings based on a clinical vignette. Your goal is to create labs and findings that are as realistic as possible.

Example:
Vignette: Ms. Smith, a 65-year-old woman, presents to the emergency department (ED) with a 3-day history of worsening shortness of breath, productive cough with yellowish sputum, and fever. She has a past medical history of hypertension, type 2 diabetes mellitus, and chronic obstructive pulmonary disease (COPD). She is a former smoker, having quit 10 years ago, and denies any recent travel, sick contacts, or exposure to tuberculosis. On further questioning, she reports feeling increasingly fatigued over the past week and has been experiencing night sweats.

Output:
Temperature: 38.5°C (101.3°F)\nBlood Pressure: 145/90 mmHg\nHeart Rate: 110 bpm\nRespiratory Rate: 22 breaths/min\nOxygen Saturation: 92% on room air\nComplete Blood Count (CBC):\n- WBC: 15,000 cells/µL (normal range: 4,500-11,000 cells/µL)\n- Hemoglobin: 12 g/dL (normal range: 12-16 g/dL)\n- Platelets: 300,000 cells/µL (normal range: 150,000-450,000 cells/µL)\nBlood Chemistry:\n- Sodium: 140 mmol/L (normal range: 135-145 mmol/L)\n- Potassium: 4.0 mmol/L (normal range: 3.5-5.0 mmol/L)\n- Creatinine: 1.0 mg/dL (normal range: 0.6-1.2 mg/dL)\n- Blood Urea Nitrogen (BUN): 20 mg/dL (normal range: 6-20 mg/dL)\n- Glucose: 180 mg/dL (normal range: 70-110 mg/dL)\nChest X-Ray: Right middle lobe consolidation consistent with pneumonia.
""".strip()
        labs = query_system(system_prompt, f"Vignette: {vignette}\n", max_tokens=256).strip()

        learning_objectives = query_learning_objectives(clinical_vignette=vignette)

        # Return JSON response
        return jsonify({
            "vignette": vignette,
            "labs": labs,
            "learning_objectives": learning_objectives
        })
    except Exception as e:
        app.logger.error(f"Error generating case: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add or update the feedback API endpoint:
@app.route('/api/generate-feedback', methods=['POST'])
def generate_feedback():
    try:
        # Get the chat history and learning objectives from the request
        chat_history = request.json.get('chat_history', [])
        vignette = request.json.get('vignette', '')
        learning_objectives = request.json.get('learning_objectives', '')
        
        # Log the request
        with open('log.txt', 'a', encoding='utf-8') as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + 
                    ' ' + request.remote_addr + ' Generating feedback\n')
        
        # Format the chat history for the LLM
        formatted_chat = ""
        for message in chat_history:
            try:
                parts = message.split(':', 1)
                if len(parts) > 1:
                    role = parts[0].strip()
                    content = parts[1].strip()
                    formatted_chat += f"{role}: {content}\n\n"
            except Exception as e:
                app.logger.error(f"Error parsing message for feedback: {str(e)}")
        
        # Create the prompt for feedback generation
        system_prompt = f"""You are a medical education professor evaluating a medical student's performance in a simulated patient encounter. 
        Provide constructive feedback on the following aspects:
        
        1. Clinical reasoning and diagnostic approach
        2. Communication skills and rapport building
        3. History taking completeness and relevance
        4. Management plan appropriateness
        
        Base your evaluation on how well the student addressed these learning objectives:
        
        {learning_objectives}
        
        For each objective, indicate whether it was met (✅) or not met (❌) and provide specific feedback.
        Conclude with 2-3 areas of strength and 2-3 areas for improvement.
        
        The clinical case was:
        {vignette}
        """
        
        # Generate the feedback
        feedback = query_system(system_prompt, formatted_chat, max_tokens=1024)
        
        return jsonify({
            'feedback': feedback,
            'success': True
        })
        
    except Exception as e:
        app.logger.error(f"Error generating feedback: {str(e)}")
        return jsonify({
            'feedback': "An error occurred while generating feedback.",
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)