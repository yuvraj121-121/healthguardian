import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# =====================
# PATTERN DETECTION
# =====================

def detect_patterns(checkins):
    if len(checkins) < 3:
        return []

    patterns = []

    energies = [c.energy for c in checkins[:14]]
    sleeps = [c.sleep for c in checkins[:14]]
    moods = [c.mood for c in checkins[:14]]
    pains = [c.pain for c in checkins[:14]]
    stresses = [c.stress for c in checkins[:14]]

    # Energy declining pattern
    if len(energies) >= 5:
        recent = np.mean(energies[:5])
        older = np.mean(energies[5:])
        if older > 0 and recent < older:
            drop_pct = round(((older - recent) / older) * 100)
            if drop_pct >= 20:
                patterns.append({
                    'type': 'warning',
                    'icon': '⚡',
                    'title': 'Energy Declining',
                    'message': f'Your energy has dropped {drop_pct}% over the past 2 weeks.',
                    'severity': 'high' if drop_pct >= 35 else 'medium'
                })

    # Poor sleep pattern
    if len(sleeps) >= 5:
        poor_sleep_days = sum(1 for s in sleeps[:7] if s <= 4)
        if poor_sleep_days >= 4:
            patterns.append({
                'type': 'warning',
                'icon': '😴',
                'title': 'Chronic Poor Sleep',
                'message': f'Poor sleep detected for {poor_sleep_days} out of last 7 days.',
                'severity': 'high'
            })

    # High stress pattern
    if len(stresses) >= 5:
        avg_stress = np.mean(stresses[:7])
        if avg_stress >= 7:
            patterns.append({
                'type': 'warning',
                'icon': '😰',
                'title': 'High Stress Pattern',
                'message': f'Your stress level has been consistently high (avg: {round(avg_stress, 1)}/10).',
                'severity': 'high'
            })

    # Pain increasing
    if len(pains) >= 5:
        recent_pain = np.mean(pains[:5])
        older_pain = np.mean(pains[5:])
        if older_pain > 0 and recent_pain > older_pain:
            increase = round(((recent_pain - older_pain) / older_pain) * 100)
            if increase >= 20:
                patterns.append({
                    'type': 'warning',
                    'icon': '💊',
                    'title': 'Pain Increasing',
                    'message': f'Your pain levels have increased {increase}% recently.',
                    'severity': 'high' if increase >= 40 else 'medium'
                })

    # Mood declining
    if len(moods) >= 5:
        recent_mood = np.mean(moods[:5])
        older_mood = np.mean(moods[5:])
        if older_mood > 0 and recent_mood < older_mood:
            drop = round(((older_mood - recent_mood) / older_mood) * 100)
            if drop >= 25:
                patterns.append({
                    'type': 'warning',
                    'icon': '😔',
                    'title': 'Mood Declining',
                    'message': f'Your mood has dropped {drop}% over recent check-ins.',
                    'severity': 'medium'
                })

    # Positive pattern
    if not patterns:
        patterns.append({
            'type': 'good',
            'icon': '✅',
            'title': 'Stable Health Patterns',
            'message': 'No concerning patterns detected. Keep up your daily check-ins!',
            'severity': 'low'
        })

    return patterns


# =====================
# ANOMALY DETECTION
# =====================

def detect_anomalies(checkins):
    if len(checkins) < 5:
        return []

    anomalies = []
    latest = checkins[0]
    historical = checkins[1:15]

    if not historical:
        return []

    avg_energy = np.mean([c.energy for c in historical])
    avg_sleep = np.mean([c.sleep for c in historical])
    avg_mood = np.mean([c.mood for c in historical])
    avg_pain = np.mean([c.pain for c in historical])
    avg_stress = np.mean([c.stress for c in historical])

    std_energy = np.std([c.energy for c in historical]) or 1
    std_sleep = np.std([c.sleep for c in historical]) or 1
    std_pain = np.std([c.pain for c in historical]) or 1

    # Energy anomaly
    if latest.energy < avg_energy - (1.5 * std_energy):
        anomalies.append({
            'metric': 'Energy',
            'current': latest.energy,
            'average': round(avg_energy, 1),
            'message': f'Energy unusually low today ({latest.energy} vs avg {round(avg_energy, 1)})'
        })

    # Sleep anomaly
    if latest.sleep < avg_sleep - (1.5 * std_sleep):
        anomalies.append({
            'metric': 'Sleep',
            'current': latest.sleep,
            'average': round(avg_sleep, 1),
            'message': f'Sleep quality unusually low today ({latest.sleep} vs avg {round(avg_sleep, 1)})'
        })

    # Pain anomaly
    if latest.pain > avg_pain + (1.5 * std_pain):
        anomalies.append({
            'metric': 'Pain',
            'current': latest.pain,
            'average': round(avg_pain, 1),
            'message': f'Pain unusually high today ({latest.pain} vs avg {round(avg_pain, 1)})'
        })

    return anomalies


# =====================
# DISEASE RISK PREDICTION
# =====================

def predict_disease_risk(checkins):
    if len(checkins) < 3:
        return []

    risks = []
    recent = checkins[:7]

    avg_energy = np.mean([c.energy for c in recent])
    avg_sleep = np.mean([c.sleep for c in recent])
    avg_mood = np.mean([c.mood for c in recent])
    avg_pain = np.mean([c.pain for c in recent])
    avg_appetite = np.mean([c.appetite for c in recent])
    avg_stress = np.mean([c.stress for c in recent])

    # Anaemia risk
    if avg_energy <= 4 and avg_appetite <= 4 and avg_mood <= 4:
        risks.append({
            'condition': 'Anaemia',
            'probability': 'Medium-High',
            'icon': '🩸',
            'symptoms': ['Low energy', 'Poor appetite', 'Low mood'],
            'recommendation': 'Get a CBC blood test. Check iron and B12 levels.',
            'color': 'red'
        })

    # Diabetes risk
    if avg_energy <= 5 and avg_appetite >= 7 and avg_stress >= 6:
        risks.append({
            'condition': 'Pre-diabetes',
            'probability': 'Medium',
            'icon': '🍬',
            'symptoms': ['Fatigue', 'High appetite', 'High stress'],
            'recommendation': 'Get fasting blood sugar test. Monitor diet.',
            'color': 'amber'
        })

    # Anxiety / Depression risk
    if avg_mood <= 4 and avg_sleep <= 4 and avg_stress >= 7:
        risks.append({
            'condition': 'Anxiety / Depression',
            'probability': 'High',
            'icon': '🧠',
            'symptoms': ['Low mood', 'Poor sleep', 'High stress'],
            'recommendation': 'Consider speaking to a mental health professional.',
            'color': 'purple'
        })

    # Burnout risk
    if avg_stress >= 7 and avg_energy <= 4 and avg_mood <= 5:
        risks.append({
            'condition': 'Burnout',
            'probability': 'High',
            'icon': '🔥',
            'symptoms': ['High stress', 'Low energy', 'Low mood'],
            'recommendation': 'Take rest. Reduce workload. See a doctor if persists.',
            'color': 'red'
        })

    # Chronic Fatigue risk
    if avg_energy <= 3 and avg_sleep >= 7 and avg_pain >= 5:
        risks.append({
            'condition': 'Chronic Fatigue Syndrome',
            'probability': 'Medium',
            'icon': '😴',
            'symptoms': ['Severe fatigue', 'Adequate sleep but still tired', 'Pain'],
            'recommendation': 'See a doctor. Get thyroid and vitamin D tests.',
            'color': 'amber'
        })

    # Hypertension risk
    if avg_stress >= 8 and avg_pain >= 6 and avg_sleep <= 4:
        risks.append({
            'condition': 'Hypertension Risk',
            'probability': 'Medium',
            'icon': '❤️',
            'symptoms': ['Very high stress', 'High pain', 'Poor sleep'],
            'recommendation': 'Check blood pressure regularly. Reduce stress.',
            'color': 'red'
        })

    return risks


# =====================
# TREND FORECASTING
# =====================

def forecast_trends(checkins):
    if len(checkins) < 7:
        return {}

    forecasts = {}
    metrics = ['energy', 'sleep', 'mood', 'pain']

    for metric in metrics:
        values = [getattr(c, metric) for c in checkins[:14]]
        values.reverse()

        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]

        current = values[-1]
        predicted = round(min(10, max(1, current + (slope * 7))), 1)

        if slope > 0.1:
            trend = 'improving'
            trend_icon = '📈'
        elif slope < -0.1:
            trend = 'declining'
            trend_icon = '📉'
        else:
            trend = 'stable'
            trend_icon = '➡️'

        forecasts[metric] = {
            'current': current,
            'predicted': predicted,
            'trend': trend,
            'trend_icon': trend_icon,
            'slope': round(slope, 2)
        }

    return forecasts


# =====================
# COMPLETE ML ANALYSIS
# =====================

def run_full_analysis(checkins):
    if len(checkins) < 1:
        return {
            'patterns': [],
            'anomalies': [],
            'risks': [],
            'forecasts': {},
            'overall_score': 0,
            'overall_status': 'No data'
        }

    patterns = detect_patterns(checkins)
    anomalies = detect_anomalies(checkins)
    risks = predict_disease_risk(checkins)
    forecasts = forecast_trends(checkins)

    # Overall health score
    recent = checkins[:7]
    avg_energy = np.mean([c.energy for c in recent])
    avg_sleep = np.mean([c.sleep for c in recent])
    avg_mood = np.mean([c.mood for c in recent])
    avg_pain = np.mean([c.pain for c in recent])

    overall_score = round(
        (avg_energy + avg_sleep + avg_mood + (10 - avg_pain)) / 4, 1
    )

    if overall_score >= 7:
        overall_status = 'Good'
    elif overall_score >= 5:
        overall_status = 'Moderate'
    else:
        overall_status = 'Needs Attention'

    return {
        'patterns': patterns,
        'anomalies': anomalies,
        'risks': risks,
        'forecasts': forecasts,
        'overall_score': overall_score,
        'overall_status': overall_status
    }