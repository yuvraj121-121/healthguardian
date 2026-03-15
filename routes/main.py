from flask import Blueprint, render_template, redirect, url_for, request
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
from report_analyzer import analyze_report
from report_analyzer import analyze_report, analyze_symptoms_with_groq

main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = 'static/uploads'

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

    return render_template('dashboard.html',
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
        progress_pct=progress_pct
    )


@main.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    filter_risk = request.args.get('risk', 'all')

    query = CheckIn.query.filter_by(user_id=current_user.id)

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
        low_count=low_count
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
        total_checkins=total_checkins
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
        total_alerts=total_alerts
    )


@main.route('/reports')
@login_required
def reports():
    user_reports = Report.query.filter_by(
        user_id=current_user.id
    ).order_by(Report.upload_date.desc()).all()

    return render_template('reports.html', reports=user_reports)


@main.route('/reports/upload', methods=['POST'])
@login_required
def upload_report():
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
        ai_analysis=ai_analysis
    )


@main.route('/reports/<int:report_id>/delete')
@login_required
def delete_report(report_id):
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
    checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.date.desc()).limit(30).all()

    analysis = run_full_analysis(checkins)

    return render_template('ml_insights.html', analysis=analysis)

@main.route('/symptoms', methods=['GET', 'POST'])
@login_required
def symptoms():
    result = None
    if request.method == 'POST':
        symptoms_text = request.form.get('symptoms')
        age = request.form.get('age', current_user.age or 25)
        gender = request.form.get('gender', current_user.gender or 'unknown')

        result = analyze_symptoms_with_groq(symptoms_text, age, gender)

    return render_template('symptoms.html', result=result)