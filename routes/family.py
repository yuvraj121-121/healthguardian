from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from extensions import db
from models.user import User
from models.family import FamilyMember
from models.checkin import CheckIn
from datetime import datetime, timedelta
import resend
import os
import secrets

family_bp = Blueprint('family', __name__)

@family_bp.route('/family')
@login_required
def family():
    if current_user.plan != 'family':
        return redirect(url_for('payment.pricing'))

    # Get all family members
    family_links = FamilyMember.query.filter_by(owner_id=current_user.id).all()
    
    members_data = []
    for link in family_links:
        member = link.member
        # Get latest checkin
        latest = CheckIn.query.filter_by(
            user_id=member.id
        ).order_by(CheckIn.date.desc()).first()

        # Get 7 day avg
        week_checkins = CheckIn.query.filter(
            CheckIn.user_id == member.id,
            CheckIn.date >= datetime.utcnow() - timedelta(days=7)
        ).all()

        avg_energy = round(sum(c.energy for c in week_checkins) / len(week_checkins), 1) if week_checkins else 0
        avg_sleep = round(sum(c.sleep for c in week_checkins) / len(week_checkins), 1) if week_checkins else 0
        avg_mood = round(sum(c.mood for c in week_checkins) / len(week_checkins), 1) if week_checkins else 0
        avg_pain = round(sum(c.pain for c in week_checkins) / len(week_checkins), 1) if week_checkins else 0

        score = round((avg_energy + avg_sleep + avg_mood + (10 - avg_pain)) / 4, 1) if week_checkins else 0

        members_data.append({
            'id': member.id,
            'name': member.fullname,
            'email': member.email,
            'relationship': link.relationship,
            'latest': latest,
            'avg_energy': avg_energy,
            'avg_sleep': avg_sleep,
            'avg_mood': avg_mood,
            'avg_pain': avg_pain,
            'score': score,
            'checkin_count': len(week_checkins),
            'profile_photo': member.profile_photo,
            'link_id': link.id
        })

    total_members = len(family_links)
    can_add = total_members < 4  # owner + 4 = 5 total

    return render_template('family.html',
        members=members_data,
        total_members=total_members,
        can_add=can_add,
        user_plan=current_user.plan
    )


@family_bp.route('/family/invite', methods=['POST'])
@login_required
def invite_member():
    if current_user.plan != 'family':
        return redirect(url_for('payment.pricing'))

    # Check limit
    count = FamilyMember.query.filter_by(owner_id=current_user.id).count()
    if count >= 4:
        flash('Family limit reached! Maximum 4 additional members allowed.', 'error')
        return redirect(url_for('family.family'))

    email = request.form.get('email')
    relationship = request.form.get('relationship', 'Family Member')

    if email == current_user.email:
        flash('You cannot add yourself!', 'error')
        return redirect(url_for('family.family'))

    # Check if user exists
    member = User.query.filter_by(email=email).first()

    if member:
        # Already registered — add directly
        existing = FamilyMember.query.filter_by(
            owner_id=current_user.id,
            member_id=member.id
        ).first()

        if existing:
            flash('This person is already in your family!', 'error')
            return redirect(url_for('family.family'))

        new_link = FamilyMember(
            owner_id=current_user.id,
            member_id=member.id,
            relationship=relationship
        )
        db.session.add(new_link)
        db.session.commit()

        # Send notification email
        try:
            resend.api_key = os.getenv('RESEND_API_KEY')
            resend.Emails.send({
                "from": "HealthGuardian <onboarding@resend.dev>",
                "to": os.getenv('MAIL_EMAIL'),
                "subject": "HealthGuardian - Added to Family",
                "text": f"""Hi {member.fullname},

{current_user.fullname} has added you to their HealthGuardian family plan!

You can now share health insights with your family.

Login at: https://web-production-28ce.up.railway.app/login

— HealthGuardian Team"""
            })
        except:
            pass

        flash(f'{member.fullname} added to your family! ✅', 'success')
    else:
        # Not registered — send invite email
        try:
            resend.api_key = os.getenv('RESEND_API_KEY')
            resend.Emails.send({
                "from": "HealthGuardian <onboarding@resend.dev>",
                "to": os.getenv('MAIL_EMAIL'),
                "subject": f"{current_user.fullname} invited you to HealthGuardian",
                "text": f"""Hi there!

{current_user.fullname} has invited you to join their family on HealthGuardian — an AI health tracking app.

Create your free account at:
https://web-production-28ce.up.railway.app/register

Once registered, ask {current_user.fullname} to add you to their family plan.

— HealthGuardian Team"""
            })
        except:
            pass

        flash(f'Invite sent to {email}! They need to register first.', 'success')

    return redirect(url_for('family.family'))


@family_bp.route('/family/remove/<int:link_id>')
@login_required
def remove_member(link_id):
    if current_user.plan != 'family':
        return redirect(url_for('payment.pricing'))

    link = FamilyMember.query.filter_by(
        id=link_id,
        owner_id=current_user.id
    ).first_or_404()

    db.session.delete(link)
    db.session.commit()
    flash('Family member removed.', 'success')
    return redirect(url_for('family.family'))