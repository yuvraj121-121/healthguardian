from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models.checkin import CheckIn
from datetime import datetime

checkin_bp = Blueprint('checkin_bp', __name__)

def calculate_risk(energy, sleep, mood, pain, appetite, stress):
    score = 0

    if energy <= 2: score += 25
    elif energy <= 3: score += 10

    if sleep <= 2: score += 20
    elif sleep <= 3: score += 8

    if mood <= 2: score += 20
    elif mood <= 3: score += 8

    if pain >= 4: score += 25
    elif pain >= 3: score += 10

    if appetite <= 2: score += 15
    elif appetite <= 3: score += 5

    if stress >= 4: score += 20
    elif stress >= 3: score += 8

    if score >= 60:
        level = 'high'
        message = '⚠️ High risk detected. Please consult a doctor soon.'
    elif score >= 30:
        level = 'medium'
        message = '⚡ Some concerning patterns detected. Monitor closely.'
    else:
        level = 'low'
        message = '✅ You are doing well! Keep it up.'

    return score, level, message


@checkin_bp.route('/checkin', methods=['GET', 'POST'])
@login_required
def checkin():
    today_checkin = CheckIn.query.filter(
        CheckIn.user_id == current_user.id,
        CheckIn.date >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).first()

    if request.method == 'POST':
        energy = int(request.form.get('energy'))
        sleep = int(request.form.get('sleep'))
        mood = int(request.form.get('mood'))
        pain = int(request.form.get('pain'))
        appetite = int(request.form.get('appetite'))
        stress = int(request.form.get('stress'))
        notes = request.form.get('notes', '')

        risk_score, risk_level, warning_message = calculate_risk(
            energy, sleep, mood, pain, appetite, stress
        )

        new_checkin = CheckIn(
            user_id=current_user.id,
            energy=energy,
            sleep=sleep,
            mood=mood,
            pain=pain,
            appetite=appetite,
            stress=stress,
            notes=notes,
            risk_score=risk_score,
            risk_level=risk_level,
            warning_message=warning_message
        )

        db.session.add(new_checkin)
        db.session.commit()

        flash(warning_message, risk_level)
        return redirect(url_for('main.dashboard'))

    return render_template('checkin.html', 
    today_checkin=today_checkin,
    user_plan=current_user.plan
)