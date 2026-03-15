from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import current_user
from extensions import db
import stripe
import os

payment_bp = Blueprint('payment', __name__)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PLANS = {
    'premium': {
        'name': 'Premium',
        'price': 499,
        'description': 'Unlimited tracking + AI features'
    },
    'family': {
        'name': 'Family',
        'price': 999,
        'description': 'Up to 5 members + All Premium features'
    }
}

@payment_bp.route('/pricing')
def pricing():
    return render_template('pricing.html',
                         stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'),
                         plans=PLANS)

@payment_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if not current_user.is_authenticated:
        session['next_after_login'] = url_for('payment.pricing')
        return redirect(url_for('auth.login'))

    plan = request.form.get('plan')
    if plan not in PLANS:
        flash('Invalid plan!', 'error')
        return redirect(url_for('payment.pricing'))

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': f"HealthGuardian {PLANS[plan]['name']}",
                        'description': PLANS[plan]['description'],
                    },
                    'unit_amount': PLANS[plan]['price'],
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            metadata={'plan': plan},
            success_url=url_for('payment.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.pricing', _external=True),
            customer_email=current_user.email,
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('payment.pricing'))

@payment_bp.route('/payment/success')
def success():
    session_id = request.args.get('session_id')
    if session_id and current_user.is_authenticated:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            plan = checkout_session.metadata.get('plan', 'premium')
            current_user.plan = plan
            current_user.stripe_customer_id = checkout_session.customer
            db.session.commit()
        except Exception as e:
            print(f'Plan update error: {e}')
    flash('Payment successful! Welcome to Premium! 🎉', 'success')
    return redirect(url_for('main.dashboard'))

@payment_bp.route('/payment/cancel')
def cancel():
    flash('Payment cancelled.', 'error')
    return redirect(url_for('payment.pricing'))