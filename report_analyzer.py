import re
import os
import base64
import fitz
from PIL import Image
from groq import Groq

groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    return groq_client

NORMAL_RANGES = {
    'hemoglobin': {'min': 13.5, 'max': 17.5, 'unit': 'g/dL', 'name': 'Hemoglobin', 'category': 'Blood Count'},
    'hb': {'min': 13.5, 'max': 17.5, 'unit': 'g/dL', 'name': 'Hemoglobin', 'category': 'Blood Count'},
    'wbc': {'min': 4000, 'max': 11000, 'unit': 'cells/µL', 'name': 'WBC Count', 'category': 'Blood Count'},
    'rbc': {'min': 4.5, 'max': 5.5, 'unit': 'million/µL', 'name': 'RBC Count', 'category': 'Blood Count'},
    'platelets': {'min': 150000, 'max': 400000, 'unit': '/µL', 'name': 'Platelets', 'category': 'Blood Count'},
    'hematocrit': {'min': 41, 'max': 53, 'unit': '%', 'name': 'Hematocrit', 'category': 'Blood Count'},
    'glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL', 'name': 'Blood Glucose', 'category': 'Blood Sugar'},
    'fasting glucose': {'min': 70, 'max': 100, 'unit': 'mg/dL', 'name': 'Fasting Glucose', 'category': 'Blood Sugar'},
    'hba1c': {'min': 4.0, 'max': 5.6, 'unit': '%', 'name': 'HbA1c', 'category': 'Blood Sugar'},
    'blood sugar': {'min': 70, 'max': 140, 'unit': 'mg/dL', 'name': 'Blood Sugar', 'category': 'Blood Sugar'},
    'tsh': {'min': 0.4, 'max': 4.0, 'unit': 'mIU/L', 'name': 'TSH', 'category': 'Thyroid'},
    't3': {'min': 80, 'max': 200, 'unit': 'ng/dL', 'name': 'T3', 'category': 'Thyroid'},
    't4': {'min': 5.0, 'max': 12.0, 'unit': 'µg/dL', 'name': 'T4', 'category': 'Thyroid'},
    'sgpt': {'min': 7, 'max': 56, 'unit': 'U/L', 'name': 'SGPT (ALT)', 'category': 'Liver'},
    'alt': {'min': 7, 'max': 56, 'unit': 'U/L', 'name': 'ALT', 'category': 'Liver'},
    'sgot': {'min': 10, 'max': 40, 'unit': 'U/L', 'name': 'SGOT (AST)', 'category': 'Liver'},
    'ast': {'min': 10, 'max': 40, 'unit': 'U/L', 'name': 'AST', 'category': 'Liver'},
    'bilirubin': {'min': 0.1, 'max': 1.2, 'unit': 'mg/dL', 'name': 'Bilirubin', 'category': 'Liver'},
    'creatinine': {'min': 0.6, 'max': 1.2, 'unit': 'mg/dL', 'name': 'Creatinine', 'category': 'Kidney'},
    'urea': {'min': 7, 'max': 20, 'unit': 'mg/dL', 'name': 'Blood Urea', 'category': 'Kidney'},
    'uric acid': {'min': 3.5, 'max': 7.2, 'unit': 'mg/dL', 'name': 'Uric Acid', 'category': 'Kidney'},
    'cholesterol': {'min': 0, 'max': 200, 'unit': 'mg/dL', 'name': 'Total Cholesterol', 'category': 'Lipid'},
    'total cholesterol': {'min': 0, 'max': 200, 'unit': 'mg/dL', 'name': 'Total Cholesterol', 'category': 'Lipid'},
    'ldl': {'min': 0, 'max': 100, 'unit': 'mg/dL', 'name': 'LDL Cholesterol', 'category': 'Lipid'},
    'hdl': {'min': 40, 'max': 999, 'unit': 'mg/dL', 'name': 'HDL Cholesterol', 'category': 'Lipid'},
    'triglycerides': {'min': 0, 'max': 150, 'unit': 'mg/dL', 'name': 'Triglycerides', 'category': 'Lipid'},
    'vitamin d': {'min': 30, 'max': 100, 'unit': 'ng/mL', 'name': 'Vitamin D', 'category': 'Vitamins'},
    'vitamin b12': {'min': 200, 'max': 900, 'unit': 'pg/mL', 'name': 'Vitamin B12', 'category': 'Vitamins'},
    'iron': {'min': 60, 'max': 170, 'unit': 'µg/dL', 'name': 'Iron', 'category': 'Vitamins'},
    'ferritin': {'min': 12, 'max': 300, 'unit': 'ng/mL', 'name': 'Ferritin', 'category': 'Vitamins'},
    'systolic': {'min': 90, 'max': 120, 'unit': 'mmHg', 'name': 'Systolic BP', 'category': 'Blood Pressure'},
    'diastolic': {'min': 60, 'max': 80, 'unit': 'mmHg', 'name': 'Diastolic BP', 'category': 'Blood Pressure'},
    'cea': {'min': 0, 'max': 2.5, 'unit': 'ng/mL', 'name': 'CEA', 'category': 'Tumor Markers'},
    'ca-125': {'min': 0, 'max': 35, 'unit': 'U/mL', 'name': 'CA-125', 'category': 'Tumor Markers'},
    'ca 125': {'min': 0, 'max': 35, 'unit': 'U/mL', 'name': 'CA-125', 'category': 'Tumor Markers'},
    'psa': {'min': 0, 'max': 4.0, 'unit': 'ng/mL', 'name': 'PSA', 'category': 'Tumor Markers'},
    'afp': {'min': 0, 'max': 10, 'unit': 'ng/mL', 'name': 'AFP', 'category': 'Tumor Markers'},
    'ca 19-9': {'min': 0, 'max': 37, 'unit': 'U/mL', 'name': 'CA 19-9', 'category': 'Tumor Markers'},
    'ca19-9': {'min': 0, 'max': 37, 'unit': 'U/mL', 'name': 'CA 19-9', 'category': 'Tumor Markers'},
    'hcg': {'min': 0, 'max': 5, 'unit': 'mIU/mL', 'name': 'HCG', 'category': 'Tumor Markers'},
    'ldh': {'min': 140, 'max': 280, 'unit': 'U/L', 'name': 'LDH', 'category': 'Tumor Markers'},
    'beta-2 microglobulin': {'min': 0.8, 'max': 2.4, 'unit': 'mg/L', 'name': 'Beta-2 Microglobulin', 'category': 'Tumor Markers'},
}


def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return ""


def analyze_image_with_groq_vision(file_path):
    try:
        with open(file_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        ext = file_path.split('.')[-1].lower()
        mime_type = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'

        response = get_groq_client().chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "You are an expert medical doctor and radiologist analyzing a medical image.\n\nAnalyze this image and respond in EXACT HTML format. No markdown, pure HTML only:\n\n<div class=\"ai-section\">\n<h3>🖼️ Image Type</h3>\n<p>Describe what type of medical image this is.</p>\n</div>\n\n<div class=\"ai-section\">\n<h3>🔍 Visual Findings</h3>\n<div class=\"risk-list\">\n<div class=\"risk-item risk-medium\">\n<div class=\"risk-name\">Finding Name</div>\n<div class=\"risk-desc\">Detailed description of finding</div>\n</div>\n</div>\n</div>\n\n<div class=\"ai-section\">\n<h3>🏥 Possible Conditions</h3>\n<div class=\"risk-list\">\n<div class=\"risk-item risk-high\">\n<div class=\"risk-name\">🔴 Condition Name</div>\n<div class=\"risk-prob\">High Risk</div>\n<div class=\"risk-desc\">Why this condition is suspected</div>\n</div>\n</div>\n</div>\n\n<div class=\"ai-section\">\n<h3>🎗️ Cancer Indicators</h3>\n<div class=\"risk-list\">\n<div class=\"risk-item risk-low\">\n<div class=\"risk-name\">✅ No Cancer Indicators</div>\n<div class=\"risk-desc\">Explanation</div>\n</div>\n</div>\n</div>\n\n<div class=\"ai-section\">\n<h3>✅ Normal Findings</h3>\n<p>List what appears completely normal.</p>\n</div>\n\n<div class=\"ai-section\">\n<h3>💊 Recommendations</h3>\n<div class=\"tips-grid\">\n<div class=\"tip-card\">\n<div class=\"tip-icon\">👨‍⚕️</div>\n<div class=\"tip-title\">Specialist</div>\n<div class=\"tip-desc\">Which doctor to see</div>\n</div>\n<div class=\"tip-card\">\n<div class=\"tip-icon\">🧪</div>\n<div class=\"tip-title\">Additional Tests</div>\n<div class=\"tip-desc\">Tests needed</div>\n</div>\n<div class=\"tip-card\">\n<div class=\"tip-icon\">⏰</div>\n<div class=\"tip-title\">Urgency</div>\n<div class=\"tip-desc\">When to see doctor</div>\n</div>\n<div class=\"tip-card\">\n<div class=\"tip-icon\">🔄</div>\n<div class=\"tip-title\">Follow-up</div>\n<div class=\"tip-desc\">Follow-up required</div>\n</div>\n</div>\n</div>\n\n<div class=\"ai-section\">\n<h3>🚨 Overall Assessment</h3>\n<div class=\"urgency-banner urgency-medium\">\nNEEDS INVESTIGATION\n<p>Brief explanation of overall finding and urgency.</p>\n</div>\n</div>\n\n<div class=\"ai-disclaimer\">\n⚕️ This AI analysis is for educational purposes only. Always consult a qualified doctor for proper medical diagnosis.\n</div>\n\nFill in real findings from the image. Use exact class names. No markdown."
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Image analysis failed: {str(e)}"


def analyze_with_groq(text):
    try:
        prompt = f"""You are an expert medical doctor and oncologist analyzing a patient's medical report.

Here is the medical report text:
{text}

Please provide a COMPREHENSIVE analysis in EXACT HTML format. No markdown, pure HTML:

<div class="ai-section">
<h3>📋 Summary</h3>
<p>Write 3-4 sentences summarizing the overall report findings in simple language.</p>
</div>

<div class="ai-section">
<h3>🔬 Test Results Analysis</h3>
<table class="ai-table">
<thead><tr><th>Test Name</th><th>Patient Value</th><th>Normal Range</th><th>Status</th><th>What It Means</th></tr></thead>
<tbody>
[Add rows for each test found]
</tbody>
</table>
</div>

<div class="ai-section">
<h3>⚠️ Disease Risk Assessment</h3>
<div class="risk-list">
[Add risk items]
</div>
</div>

<div class="ai-section">
<h3>💊 Recommendations</h3>
<div class="tips-grid">
<div class="tip-card">
<div class="tip-icon">🥗</div>
<div class="tip-title">Diet Changes</div>
<div class="tip-desc">Specific diet recommendations</div>
</div>
<div class="tip-card">
<div class="tip-icon">🏃</div>
<div class="tip-title">Lifestyle</div>
<div class="tip-desc">Specific lifestyle changes</div>
</div>
<div class="tip-card">
<div class="tip-icon">👨‍⚕️</div>
<div class="tip-title">Doctor Visit</div>
<div class="tip-desc">Which specialist and urgency</div>
</div>
<div class="tip-card">
<div class="tip-icon">🧪</div>
<div class="tip-title">Follow-up Tests</div>
<div class="tip-desc">Additional tests needed</div>
</div>
</div>
</div>

<div class="ai-section">
<h3>🚨 Urgency Level</h3>
<div class="urgency-banner urgency-medium">
ASSESSMENT
<p>Brief explanation of urgency</p>
</div>
</div>

<div class="ai-disclaimer">
⚕️ This AI analysis is for educational purposes only. Please consult a qualified doctor for proper medical diagnosis and treatment.
</div>"""

        response = get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical AI that outputs structured HTML analysis. Always use the exact HTML format provided. Be specific, clear and compassionate."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=3000
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI analysis failed: {str(e)}"


def analyze_symptoms_with_groq(symptoms, age, gender):
    try:
        prompt = f"""You are an expert medical doctor. A patient has described their symptoms.

Patient Info:
- Age: {age}
- Gender: {gender}
- Symptoms: {symptoms}

Respond in EXACT HTML format. No markdown, pure HTML:

<div class="ai-section">
<h3>🔍 Symptom Analysis</h3>
<p>Brief analysis of the symptoms described.</p>
</div>

<div class="ai-section">
<h3>🏥 Possible Conditions</h3>
<div class="risk-list">
<div class="risk-item risk-high">
<div class="risk-name">🔴 Condition Name</div>
<div class="risk-prob">High Likelihood</div>
<div class="risk-desc">Why this condition matches the symptoms</div>
</div>
</div>
</div>

<div class="ai-section">
<h3>💊 Common Medicines</h3>
<table class="ai-table">
<thead>
<tr>
<th>Medicine</th>
<th>Type</th>
<th>Common Use</th>
<th>Dosage (General)</th>
<th>Side Effects</th>
</tr>
</thead>
<tbody>
<tr class="row-normal">
<td>Medicine Name</td>
<td>Type</td>
<td>What it treats</td>
<td>General dosage info</td>
<td>Common side effects</td>
</tr>
</tbody>
</table>
</div>

<div class="ai-section">
<h3>🚫 Medicine Warnings</h3>
<div class="risk-list">
<div class="risk-item risk-high">
<div class="risk-name">⚠️ Important Warning</div>
<div class="risk-desc">Specific warning about these medicines</div>
</div>
</div>
</div>

<div class="ai-section">
<h3>🏠 Home Remedies</h3>
<div class="tips-grid">
<div class="tip-card">
<div class="tip-icon">🌿</div>
<div class="tip-title">Remedy Name</div>
<div class="tip-desc">How to use it</div>
</div>
</div>
</div>

<div class="ai-section">
<h3>🚨 When To See Doctor IMMEDIATELY</h3>
<div class="urgency-banner urgency-high">
⚠️ CONSULT DOCTOR BEFORE TAKING ANY MEDICINE
<p>List red flag symptoms that need immediate medical attention</p>
</div>
</div>

<div class="ai-disclaimer">
⚕️ IMPORTANT: This is for educational purposes only. NEVER take medicine without consulting a qualified doctor first.
</div>"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful medical AI. Always emphasize consulting a real doctor before taking any medicine."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=3000
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Analysis failed: {str(e)}"


def analyze_report_text(text):
    results = []
    lines = text.split('\n')

    for line in lines:
        line_lower = line.lower()
        for key, info in NORMAL_RANGES.items():
            if key in line_lower:
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    for num_str in numbers:
                        value = float(num_str)
                        if value > 0.01:
                            status = get_status(value, info['min'], info['max'])
                            if status:
                                results.append({
                                    'name': info['name'],
                                    'value': value,
                                    'unit': info['unit'],
                                    'min': info['min'],
                                    'max': info['max'],
                                    'status': status['status'],
                                    'status_icon': status['icon'],
                                    'status_color': status['color'],
                                    'message': status['message'],
                                    'category': info['category']
                                })
                                break

    seen = set()
    unique_results = []
    for r in results:
        if r['name'] not in seen:
            seen.add(r['name'])
            unique_results.append(r)

    return unique_results


def get_status(value, min_val, max_val):
    if value < min_val:
        diff_pct = round(((min_val - value) / min_val) * 100)
        if diff_pct >= 20:
            return {
                'status': 'critically_low',
                'icon': '🔴',
                'color': 'red',
                'message': f'Critically LOW — {diff_pct}% below normal range'
            }
        return {
            'status': 'low',
            'icon': '🟡',
            'color': 'amber',
            'message': f'LOW — below normal range ({min_val} - {max_val})'
        }
    elif value > max_val:
        diff_pct = round(((value - max_val) / max_val) * 100)
        if diff_pct >= 20:
            return {
                'status': 'critically_high',
                'icon': '🔴',
                'color': 'red',
                'message': f'Critically HIGH — {diff_pct}% above normal range'
            }
        return {
            'status': 'high',
            'icon': '🟡',
            'color': 'amber',
            'message': f'HIGH — above normal range ({min_val} - {max_val})'
        }
    else:
        return {
            'status': 'normal',
            'icon': '🟢',
            'color': 'green',
            'message': f'Normal range ({min_val} - {max_val})'
        }


def generate_summary(results, ai_analysis=None):
    if not results and not ai_analysis:
        return {
            'total': 0,
            'normal': 0,
            'abnormal': 0,
            'critical': 0,
            'overall': 'unknown',
            'recommendation': 'Could not extract values from report.',
            'urgent': False,
            'ai_analysis': ai_analysis
        }

    normal = sum(1 for r in results if r['status'] == 'normal')
    abnormal = sum(1 for r in results if r['status'] in ['low', 'high', 'critically_low', 'critically_high'])
    critical = sum(1 for r in results if r['status'] in ['critically_low', 'critically_high'])

    if critical >= 2:
        overall = 'Critical'
        recommendation = '🚨 Multiple critical values. See a doctor IMMEDIATELY.'
        urgent = True
    elif critical == 1:
        overall = 'Concerning'
        recommendation = '⚠️ Critical value detected. See a doctor within 24-48 hours.'
        urgent = True
    elif abnormal >= 3:
        overall = 'Needs Attention'
        recommendation = '💊 Several values outside normal range. Schedule a doctor visit.'
        urgent = False
    elif abnormal >= 1:
        overall = 'Minor Issues'
        recommendation = '📋 Some values slightly outside range. Monitor closely.'
        urgent = False
    else:
        overall = 'All Normal'
        recommendation = '✅ All detected values within normal range!'
        urgent = False

    return {
        'total': len(results),
        'normal': normal,
        'abnormal': abnormal,
        'critical': critical,
        'overall': overall,
        'recommendation': recommendation,
        'urgent': urgent,
        'ai_analysis': ai_analysis
    }


def analyze_report(file_path, file_type):
    if file_type == 'pdf':
        text = extract_text_from_pdf(file_path)

        if not text.strip():
            return {
                'success': False,
                'error': 'Could not extract text from PDF.',
                'results': [],
                'summary': generate_summary([])
            }

        results = analyze_report_text(text)
        ai_analysis = analyze_with_groq(text)

    else:
        results = []
        ai_analysis = analyze_image_with_groq_vision(file_path)

        try:
            import pytesseract
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            if text.strip():
                results = analyze_report_text(text)
        except:
            pass

    summary = generate_summary(results, ai_analysis)

    categories = {}
    for r in results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    return {
        'success': True,
        'results': results,
        'categories': categories,
        'summary': summary,
        'ai_analysis': ai_analysis
    }