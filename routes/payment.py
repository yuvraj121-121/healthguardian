from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
import stripe
import os

payment_bp = Blueprint('payment', __name__)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PLANS = {
    'premium': {
        'name': 'Premium',
        'price': 499,  # pence mein (£4.99)
        'description': 'Unlimited tracking + AI features'
    },
    'family': {
        'name': 'Family',
        'price': 999,  # pence mein (£9.99)
        'description': 'Up to 5 members + All Premium features'
    }
}

@payment_bp.route('/pricing')
def pricing():
    return render_template('pricing.html', 
                         stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY'),
                         plans=PLANS)

@payment_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    plan = request.form.get('plan')
    if plan not in PLANS:
        flash('Invalid plan!', 'error')
        return redirect(url_for('payment.pricing'))
    
    try:
        session = stripe.checkout.Session.create(
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
            success_url=url_for('payment.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.pricing', _external=True),
            customer_email=current_user.email,
        )
        return redirect(session.url, code=303)
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('payment.pricing'))

@payment_bp.route('/payment/success')
@login_required
def success():
    flash('Payment successful! Welcome to Premium! 🎉', 'success')
    return redirect(url_for('main.dashboard'))

@payment_bp.route('/payment/cancel')
def cancel():
    flash('Payment cancelled.', 'error')
    return redirect(url_for('payment.pricing'))