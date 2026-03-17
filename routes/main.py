from flask import Blueprint, render_template, redirect, url_for, request, make_response
from flask_login import login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models.checkin import CheckIn
from models.user import User
from models.report import Report
from datetime import datetime, timedelta
import os
import json
import calendar
from werkzeug.utils import secure_filename
from ml_model import run_full_analysis
from report_analyzer import analyze_report, analyze_symptoms_with_groq
import cloudinary
import cloudinary.uploader

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/uploads'

cloudinary.config(
    cloudinary_url=os.environ.get('CLOUDINARY_URL')
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@main.route('/dashboard')
@login_required
def dashboard():
    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

    last_7 = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date >= datetime.utcnow() - timedelta(days=7)
    ).order_by(CheckIn.date.asc()).all()

    last_week = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date >= datetime.utcnow() - timedelta(days=14),
        CheckIn.date < datetime.utcnow() - timedelta(days=7)
    ).all()

    today_checkin = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).first()

    this_month = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    ).count()

    days_in_month = calendar.monthrange(
        datetime.utcnow().year,
        datetime.utcnow().month
    )[1]

    progress_pct = round((this_month / days_in_month) * 100)

    avg_energy = round(sum(c.energy for c in checkins) / len(checkins), 1) if checkins else 0
    avg_sleep = round(sum(c.sleep for c in checkins) / len(checkins), 1) if checkins else 0
    avg_mood = round(sum(c.mood for c in checkins) / len(checkins), 1) if checkins else 0
    avg_pain = round(sum(c.pain for c in checkins) / len(checkins), 1) if checkins else 0

    lw_energy = round(sum(c.energy for c in last_week) / len(last_week), 1) if last_week else 0
    lw_sleep = round(sum(c.sleep for c in last_week) / len(last_week), 1) if last_week else 0
    lw_mood = round(sum(c.mood for c in last_week) / len(last_week), 1) if last_week else 0

    energy_change = round(avg_energy - lw_energy, 1) if lw_energy else 0
    sleep_change = round(avg_sleep - lw_sleep, 1) if lw_sleep else 0
    mood_change = round(avg_mood - lw_mood, 1) if lw_mood else 0

    tips = []
    if checkins:
        if avg_energy < 5:
            tips.append("⚡ Your energy is low. Try a 20-min walk daily.")
        if avg_sleep < 6:
            tips.append("😴 Poor sleep detected. Try sleeping before 10pm.")
        if avg_mood < 5:
            tips.append("😊 Mood seems low. Try 10 mins of sunlight daily.")
        if avg_pain >= 5:
            tips.append("💊 Pain levels are high. Consider seeing a doctor.")
        if not tips:
            tips.append("✅ You're doing great! Keep up the daily check-ins.")

    chart_labels = [c.date.strftime('%d %b') for c in last_7]
    chart_energy = [c.energy for c in last_7]
    chart_sleep = [c.sleep for c in last_7]
    chart_mood = [c.mood for c in last_7]

    warnings = [c for c in checkins if c.risk_level in ['high', 'medium']]

    streak = current_user.streak or 0
    max_streak = current_user.max_streak or 0

    return render_template('dashboard.html',
        streak=streak,
        max_streak=max_streak,
        streak=streak,
        max_streak=max_streak,
        streak=streak,
        max_streak=max_streak,
        streak=streak,
        max_streak=max_streak,
        checkins=checkins,
        today_checkin=today_checkin,
        avg_energy=avg_energy,
        avg_sleep=avg_sleep,
        avg_mood=avg_mood,
        avg_pain=avg_pain,
        energy_change=energy_change,
        sleep_change=sleep_change,
        mood_change=mood_change,
        chart_labels=chart_labels,
        chart_energy=chart_energy,
        chart_sleep=chart_sleep,
        chart_mood=chart_mood,
        warnings=warnings,
        tips=tips,
        this_month=this_month,
        days_in_month=days_in_month,
        progress_pct=progress_pct,
        user_plan=current_user.plan
    )


@main.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    filter_risk = request.args.get('risk', 'all')

    query = CheckIn.query.filter_by(user_id=current_user.id)

    # 30 days limit for free users
    if current_user.plan == 'free':
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        query = query.filter(CheckIn.date >= thirty_days_ago)

    if filter_risk != 'all':
        query = query.filter_by(risk_level=filter_risk)

    checkins = query.order_by(CheckIn.date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    total = CheckIn.query.filter_by(user_id=current_user.id).count()
    high_count = CheckIn.query.filter_by(user_id=current_user.id, risk_level='high').count()
    medium_count = CheckIn.query.filter_by(user_id=current_user.id, risk_level='medium').count()
    low_count = CheckIn.query.filter_by(user_id=current_user.id, risk_level='low').count()

    return render_template('history.html',
        checkins=checkins,
        filter_risk=filter_risk,
        total=total,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        user_plan=current_user.plan
    )


@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            current_user.fullname = request.form.get('fullname')
            current_user.age = request.form.get('age')
            current_user.gender = request.form.get('gender')

            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and file.filename != '' and allowed_file(file.filename):
                    try:
                        result = cloudinary.uploader.upload(
                            file,
                            folder="healthguardian",
                            public_id=f"profile_{current_user.id}",
                            overwrite=True,
                            transformation=[{
                                'width': 200,
                                'height': 200,
                                'crop': 'fill',
                                'gravity': 'face'
                            }]
                        )
                        current_user.profile_photo = result['secure_url']
                    except Exception as e:
                        print(f"Cloudinary upload error: {e}")

            db.session.commit()
            return redirect(url_for('main.settings') + '?msg=profile_updated')

        elif action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            if not check_password_hash(current_user.password, old_password):
                return redirect(url_for('main.settings') + '?msg=wrong_password')
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            return redirect(url_for('main.settings') + '?msg=password_updated')

    msg = request.args.get('msg', '')
    total_checkins = CheckIn.query.filter_by(user_id=current_user.id).count()

    return render_template('settings.html',
        msg=msg,
        total_checkins=total_checkins,
        user_plan=current_user.plan
    )


@main.route('/delete-checkins')
@login_required
def delete_checkins():
    CheckIn.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('main.settings') + '?msg=checkins_deleted')


@main.route('/delete-account')
@login_required
def delete_account():
    CheckIn.query.filter_by(user_id=current_user.id).delete()
    User.query.filter_by(id=current_user.id).delete()
    db.session.commit()
    logout_user()
    return redirect(url_for('main.index'))


@main.route('/alerts')
@login_required
def alerts():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    high_alerts = CheckIn.query.filter_by(
        user_id=current_user.id,
        risk_level='high'
    ).order_by(CheckIn.date.desc()).all()

    medium_alerts = CheckIn.query.filter_by(
        user_id=current_user.id,
        risk_level='medium'
    ).order_by(CheckIn.date.desc()).all()

    total_alerts = len(high_alerts) + len(medium_alerts)

    return render_template('alerts.html',
        high_alerts=high_alerts,
        medium_alerts=medium_alerts,
        total_alerts=total_alerts,
        user_plan=current_user.plan
    )


@main.route('/reports')
@login_required
def reports():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    user_reports = Report.query.filter_by(
        user_id=current_user.id
    ).order_by(Report.upload_date.desc()).all()

    return render_template('reports.html',
        reports=user_reports,
        user_plan=current_user.plan
    )


@main.route('/reports/upload', methods=['POST'])
@login_required
def upload_report():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    if 'file' not in request.files:
        return redirect(url_for('main.reports') + '?error=no_file')

    file = request.files['file']

    if file.filename == '':
        return redirect(url_for('main.reports') + '?error=no_file')

    if not allowed_file(file.filename):
        return redirect(url_for('main.reports') + '?error=invalid_type')

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(file_path)

    file_type = 'pdf' if ext == 'pdf' else 'image'
    analysis = analyze_report(file_path, file_type)

    new_report = Report(
        user_id=current_user.id,
        filename=unique_filename,
        original_name=file.filename,
        file_type=file_type,
        total_values=analysis['summary']['total'],
        normal_values=analysis['summary']['normal'],
        abnormal_values=analysis['summary']['abnormal'],
        critical_values=analysis['summary']['critical'],
        overall_status=analysis['summary']['overall'],
        recommendation=analysis['summary']['recommendation'],
        urgent=analysis['summary']['urgent'],
        raw_results=json.dumps(analysis['results']),
        ai_analysis=analysis['summary'].get('ai_analysis', '')
    )

    db.session.add(new_report)
    db.session.commit()

    return redirect(url_for('main.report_detail', report_id=new_report.id))


@main.route('/reports/<int:report_id>')
@login_required
def report_detail(report_id):
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    report = Report.query.filter_by(
        id=report_id,
        user_id=current_user.id
    ).first_or_404()

    results = json.loads(report.raw_results) if report.raw_results else []
    ai_analysis = report.ai_analysis

    categories = {}
    for r in results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    return render_template('report_detail.html',
        report=report,
        results=results,
        categories=categories,
        ai_analysis=ai_analysis,
        user_plan=current_user.plan
    )


@main.route('/reports/<int:report_id>/delete')
@login_required
def delete_report(report_id):
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    report = Report.query.filter_by(
        id=report_id,
        user_id=current_user.id
    ).first_or_404()

    file_path = os.path.join(UPLOAD_FOLDER, report.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(report)
    db.session.commit()

    return redirect(url_for('main.reports'))


@main.route('/ml-insights')
@login_required
def ml_insights():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

    analysis = run_full_analysis(checkins)

    return render_template('ml_insights.html',
        analysis=analysis,
        user_plan=current_user.plan
    )


@main.route('/symptoms', methods=['GET', 'POST'])
@login_required
def symptoms():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    result = None
    if request.method == 'POST':
        symptoms_text = request.form.get('symptoms')
        age = request.form.get('age', current_user.age or 25)
        gender = request.form.get('gender', current_user.gender or 'unknown')
        result = analyze_symptoms_with_groq(symptoms_text, age, gender)

    return render_template('symptoms.html',
        result=result,
        user_plan=current_user.plan
    )


@main.route('/export-pdf')
@login_required
def export_pdf():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))

    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

@main.route('/support')
@login_required
def support():
    return render_template('support.html',
        user_plan=current_user.plan
    )

@main.route('/health-ai', methods=['GET', 'POST'])
@login_required
def health_ai():
    if current_user.plan == 'free':
        return redirect(url_for('payment.pricing'))
    return render_template('health_ai.html',
        user_plan=current_user.plan
    )

@main.route('/health-ai/chat', methods=['POST'])
@login_required
def health_ai_chat():
    if current_user.plan == 'free':
        return {'error': 'Premium required'}, 403

    user_message = request.json.get('message')

    # Get user's health data
    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

    # Build health summary
    if checkins:
        avg_energy = round(sum(c.energy for c in checkins) / len(checkins), 1)
        avg_sleep = round(sum(c.sleep for c in checkins) / len(checkins), 1)
        avg_mood = round(sum(c.mood for c in checkins) / len(checkins), 1)
        avg_pain = round(sum(c.pain for c in checkins) / len(checkins), 1)
        avg_stress = round(sum(c.stress for c in checkins) / len(checkins), 1)
        recent = checkins[0]

        health_context = f"""
User: {current_user.fullname}, Age: {current_user.age or 'Unknown'}, Gender: {current_user.gender or 'Unknown'}
Plan: {current_user.plan}

Last 30 days averages ({len(checkins)} check-ins):
- Energy: {avg_energy}/10
- Sleep: {avg_sleep}/10
- Mood: {avg_mood}/10
- Pain: {avg_pain}/10
- Stress: {avg_stress}/10

Latest check-in ({recent.date.strftime('%d %b %Y')}):
- Energy: {recent.energy}, Sleep: {recent.sleep}, Mood: {recent.mood}
- Pain: {recent.pain}, Stress: {recent.stress}
- Risk Level: {recent.risk_level}
- Notes: {recent.notes or 'None'}

Recent risk levels: {', '.join([c.risk_level for c in checkins[:7]])}
"""
    else:
        health_context = f"User: {current_user.fullname}. No check-in data available yet."

    # Call Groq API
    from groq import Groq
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": f"""You are HealthGuardian AI — a personal health assistant. 
You have access to the user's real health data and provide personalized, accurate health insights.
Always be empathetic, clear and helpful. Never give dangerous medical advice — always recommend seeing a doctor for serious issues.
Keep responses concise but informative. Use emojis sparingly.

USER'S HEALTH DATA:
{health_context}

Respond in the same language the user writes in."""
            },
            {
                "role": "user", 
                "content": user_message
            }
        ],
        max_tokens=500,
        temperature=0.7
    )

    ai_response = response.choices[0].message.content

    return {'response': ai_response}

    avg_energy = round(sum(c.energy for c in checkins) / len(checkins), 1) if checkins else 0
    avg_sleep = round(sum(c.sleep for c in checkins) / len(checkins), 1) if checkins else 0
    avg_mood = round(sum(c.mood for c in checkins) / len(checkins), 1) if checkins else 0
    avg_pain = round(sum(c.pain for c in checkins) / len(checkins), 1) if checkins else 0

    html = f"""
    <html>
    <head><style>
        body {{ font-family: Arial, sans-serif; padding: 40px; color: #333; }}
        h1 {{ color: #7C3AED; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #7C3AED; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .stat {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .stat-val {{ font-size: 28px; font-weight: bold; color: #7C3AED; }}
        .stat-label {{ font-size: 13px; color: #666; }}
    </style></head>
    <body>
        <h1>⚡ HealthGuardian — Health Report</h1>
        <p style="color:#666;">Generated for <strong>{current_user.fullname}</strong> on {datetime.utcnow().strftime('%d %B %Y')}</p>
        <hr>
        <h2>📊 30-Day Averages</h2>
        <div class="stat"><div class="stat-val">{avg_energy}/10</div><div class="stat-label">Avg Energy</div></div>
        <div class="stat"><div class="stat-val">{avg_sleep}/10</div><div class="stat-label">Avg Sleep</div></div>
        <div class="stat"><div class="stat-val">{avg_mood}/10</div><div class="stat-label">Avg Mood</div></div>
        <div class="stat"><div class="stat-val">{avg_pain}/10</div><div class="stat-label">Avg Pain</div></div>
        <h2>📋 Check-in History</h2>
        <table>
            <tr><th>Date</th><th>Energy</th><th>Sleep</th><th>Mood</th><th>Pain</th><th>Risk</th></tr>
            {"".join(f"<tr><td>{c.date.strftime('%d %b %Y')}</td><td>{c.energy}</td><td>{c.sleep}</td><td>{c.mood}</td><td>{c.pain}</td><td>{c.risk_level.upper()}</td></tr>" for c in checkins)}
        </table>
        <p style="margin-top:40px;color:#999;font-size:12px;">This report is generated by HealthGuardian AI. Always consult a doctor for medical advice.</p>
    </body>
    </html>
    """
@main.route('/health-ai/stats')
@login_required
def health_ai_stats():
    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

    if not checkins:
        return {'avg_energy': 0, 'avg_sleep': 0, 'avg_mood': 0, 'avg_pain': 0}

    return {
        'avg_energy': round(sum(c.energy for c in checkins) / len(checkins), 1),
        'avg_sleep': round(sum(c.sleep for c in checkins) / len(checkins), 1),
        'avg_mood': round(sum(c.mood for c in checkins) / len(checkins), 1),
        'avg_pain': round(sum(c.pain for c in checkins) / len(checkins), 1)
    }

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html'
    response.headers['Content-Disposition'] = 'attachment; filename=health-report.html'
    return response