import os
import io
import csv
import sqlite3
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from flask import Flask, render_template_string, request, session, redirect, url_for, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))  # Use environment variable for secret key
app.config['SESSION_COOKIE_SECURE'] = True  # Secure cookies in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session timeout after 1 hour

# Database configuration
DATABASE = 'healthbuddy.db'


def init_db():
    """Initialize the SQLite database with required tables."""
    try:
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS health_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weight REAL NOT NULL,
                    height REAL NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    activity_level TEXT NOT NULL,
                    water_intake REAL NOT NULL,
                    health_tips TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            ''')
            # Create default admin if not exists
            c.execute("SELECT * FROM users WHERE username = 'admin'")
            if not c.fetchone():
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                          ('admin', generate_password_hash('admin123')))
            conn.commit()
            logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")


def calculate_water_intake(weight, activity_level):
    """Calculate recommended daily water intake based on weight and activity level."""
    base_ml_per_kg = 30
    activity_multipliers = {'high': 5, 'moderate': 2.5, 'low': 0}
    water_ml = weight * (base_ml_per_kg + activity_multipliers.get(activity_level, 0))
    return round(water_ml / 1000, 2)


def calculate_bmi(weight, height):
    """Calculate BMI based on weight and height."""
    return round(weight / ((height / 100) ** 2), 2)


def generate_health_tips(age, gender, weight, height, activity_level, lang="en"):
    """Generate personalized health tips based on user input."""
    bmi = calculate_bmi(weight, height)
    translations = {
        "en": {
            "bmi_underweight": "Your BMI suggests you may be underweight. Consider consulting a nutritionist.",
            "bmi_healthy": "Your BMI is in the healthy range. Maintain a balanced diet and regular exercise.",
            "bmi_overweight": "Your BMI indicates you may be overweight. Increase physical activity and follow a balanced diet.",
            "bmi_obese": "Your BMI suggests obesity. Consult a healthcare professional for personalized advice.",
            "activity_low": "Aim for at least 150 minutes of moderate exercise per week.",
            "activity_moderate": "Great job staying moderately active! Add strength training 2-3 times per week.",
            "activity_high": "You're highly active! Ensure proper recovery with adequate sleep and hydration.",
            "sleep": "Aim for 7-9 hours of sleep per night to support overall health.",
            "diet": "Include a variety of fruits, vegetables, lean proteins, and whole grains in your diet."
        },
        "sw": {
            "bmi_underweight": "BMI yako inaonyesha unaweza kuwa na uzito wa chini. Fikiria kushauriana na mtaalamu wa lishe.",
            "bmi_healthy": "BMI yako iko katika kiwango cha afya. Endelea kudumisha chakula bora na mazoezi ya mara kwa mara.",
            "bmi_overweight": "BMI yako inaonyesha unaweza kuwa na uzito wa ziada. Ongeza shughuli za kimwili na fuata chakula bora.",
            "bmi_obese": "BMI yako inaonyesha unene. Shauriana na mtaalamu wa afya kwa ushauri wa kibinafsi.",
            "activity_low": "Lenga angalau dakika 150 za mazoezi ya wastani kwa wiki.",
            "activity_moderate": "Kazi nzuri kwa kuendelea na shughuli za wastani! Ongeza mafunzo ya nguvu mara 2-3 kwa wiki.",
            "activity_high": "Wewe ni mwenye shughuli za juu! Hakikisha unapata nafuu ya kutosha na usingizi wa kutosha na maji.",
            "sleep": "Lenga kulala saa 7-9 kila usiku ili kusaidia afya ya jumla.",
            "diet": "Jumuisha aina mbalimbali za matunda, mboga, protini zisizo na mafuta, na nafaka za jumla katika chakula chako."
        }
    }
    t = translations.get(lang, translations["en"])
    tips = []
    if bmi < 18.5:
        tips.append(t["bmi_underweight"])
    elif 18.5 <= bmi < 25:
        tips.append(t["bmi_healthy"])
    elif 25 <= bmi < 30:
        tips.append(t["bmi_overweight"])
    else:
        tips.append(t["bmi_obese"])
    tips.append(t[f"activity_{activity_level}"])
    tips.extend([t["sleep"], t["diet"]])
    return tips


def send_health_report(email, result, lang="en"):
    """Send personalized health report via email."""
    translations = {
        "en": {
            "subject": "Your HealthBuddy Report",
            "greeting": "Hello, here is your personalized health report from HealthBuddy:",
            "weight": "Weight",
            "height": "Height",
            "age": "Age",
            "gender": "Gender",
            "activity_level": "Activity Level",
            "water_intake": "Recommended Daily Water Intake",
            "health_tips": "Personalized Health Tips",
            "disclaimer": "Disclaimer: This report is for informational purposes only and does not replace professional medical advice."
        },
        "sw": {
            "subject": "Ripoti Yako ya HealthBuddy",
            "greeting": "Habari, hii ni ripoti yako ya kibinafsi ya afya kutoka HealthBuddy:",
            "weight": "Uzito",
            "height": "Urefu",
            "age": "Umri",
            "gender": "Jinsia",
            "activity_level": "Kiwango cha Shughuli",
            "water_intake": "Ulaji wa Maji wa Kila Siku Unaopendekezwa",
            "health_tips": "Vidokezo vya Afya vya Kibinafsi",
            "disclaimer": "Kanusho: Ripoti hii ni kwa madhumuni ya taarifa tu na haiwezi kuchukua nafasi ya ushauri wa kitaalamu wa matibabu."
        }
    }
    t = translations.get(lang, translations["en"])
    msg = MIMEMultipart()
    msg['From'] = os.environ.get('EMAIL_SENDER', 'your_email@example.com')
    msg['To'] = email
    msg['Subject'] = t["subject"]
    health_tips_formatted = '\n- '.join(result['health_tips'])
    body = f"""
{t["greeting"]}

{t["weight"]}: {result['weight']} kg
{t["height"]}: {result['height']} cm
{t["age"]}: {result['age']}
{t["gender"]}: {result['gender'].capitalize()}
{t["activity_level"]}: {result['activity_level'].capitalize()}
{t["water_intake"]}: {result['water_intake']} liters
{t["health_tips"]}:
- {health_tips_formatted}

{t["disclaimer"]}
"""
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP(os.environ.get('SMTP_SERVER', 'smtp.gmail.com'), 587) as server:
            server.starttls()
            server.login(os.environ.get('EMAIL_SENDER'), os.environ.get('EMAIL_PASSWORD'))
            server.send_message(msg)
            logger.info(f"Health report sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")


@app.route("/", methods=["GET", "POST"])
def index():
    """Handle main page with health form and results."""
    lang = request.args.get('lang', 'en')
    init_db()
    translations = {
        "en": {
            "title": "HealthBuddy - Your Wellness Companion",
            "intro": "Your personal wellness companion – enter your details for tailored health advice!",
            "learn_health": "Learn About Healthy Living",
            "weight_label": "Weight (kg):",
            "height_label": "Height (cm):",
            "age_label": "Age:",
            "gender_label": "Gender:",
            "activity_label": "Activity Level:",
            "email_label": "Email (optional, for report):",
            "submit": "Get Your Health Advice",
            "select_gender": "Select gender",
            "select_activity": "Select activity level",
            "male": "Male",
            "female": "Female",
            "other": "Other",
            "low": "Low (sedentary)",
            "moderate": "Moderate (light exercise)",
            "high": "High (active, regular exercise)",
            "report_title": "Your Personalized Health Report",
            "water_intake_title": "Recommended Daily Water Intake",
            "health_tips_title": "Personalized Health Tips",
            "bmi_label": "BMI:",
            "dialog_title": "Healthy Living Tips",
            "dialog_content": """
                Adopting a healthy lifestyle can significantly improve your well-being. Here are some key tips:
                <ul>
                    <li><strong>Stay Hydrated:</strong> Drink adequate water daily, tailored to your weight and activity level. <a href="https://www.who.int/news-room/fact-sheets/detail/drinking-water" target="_blank">Learn more</a>.</li>
                    <li><strong>Balanced Diet:</strong> Include a variety of nutrient-rich foods like fruits, vegetables, and lean proteins. <a href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" target="_blank">Learn more</a>.</li>
                    <li><strong>Regular Exercise:</strong> Aim for at least 150 minutes of moderate activity per week. <a href="https://www.cdc.gov/physical-activity-basics/index.html" target="_blank">Learn more</a>.</li>
                    <li><strong>Adequate Sleep:</strong> Prioritize 7-9 hours of quality sleep each night. <a href="https://www.sleepfoundation.org/how-sleep-works" target="_blank">Learn more</a>.</li>
                    <li><strong>Mental Health:</strong> Practice stress management through mindfulness or hobbies. <a href="https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/mindfulness" target="_blank">Learn more</a>.</li>
                </ul>
            """,
            "dialog_close": "Close",
            "about_us_label": "About Us",
            "about_us_content": "HealthBuddy is dedicated to providing personalized health advice to help you live a healthier life.",
            "disclaimer_label": "Disclaimer",
            "disclaimer_content": "This application does not replace professional medical advice. Always consult a healthcare provider for medical concerns.",
            "copyright": "© 2025 HealthToTech. All rights reserved.",
            "error_weight": "Please enter a valid positive weight.",
            "error_height": "Please enter a valid positive height.",
            "error_age": "Please enter a valid positive age.",
            "error_email": "Please enter a valid email address."
        },
        "sw": {
            "title": "HealthBuddy - Rafiki Yako wa Afya",
            "intro": "Rafiki yako wa kibinafsi wa afya – ingiza maelezo yako kwa ushauri wa afya wa kibinafsi!",
            "learn_health": "Jifunze Kuhusu Maisha ya Afya",
            "weight_label": "Uzito (kg):",
            "height_label": "Urefu (cm):",
            "age_label": "Umri:",
            "gender_label": "Jinsia:",
            "activity_label": "Kiwango cha Shughuli:",
            "email_label": "Barua Pepe (hiari, kwa ripoti):",
            "submit": "Pata Ushauri Wako wa Afya",
            "select_gender": "Chagua jinsia",
            "select_activity": "Chagua kiwango cha shughuli",
            "male": "Mwanaume",
            "female": "Mwanamke",
            "other": "Nyingine",
            "low": "Chini (kukaa tu)",
            "moderate": "Wastani (mazoezi mepesi)",
            "high": "Juu (shughuli za mara kwa mara)",
            "report_title": "Ripoti Yako ya Afya ya Kibinafsi",
            "water_intake_title": "Ulaji wa Maji wa Kila Siku Unaopendekezwa",
            "health_tips_title": "Vidokezo vya Afya vya Kibinafsi",
            "bmi_label": "BMI:",
            "dialog_title": "Vidokezo vya Maisha ya Afya",
            "dialog_content": """
                Kuchukua mtindo wa maisha ya afya kunaweza kuboresha ustawi wako kwa kiasi kikubwa. Hapa kuna vidokezo vya msingi:
                <ul>
                    <li><strong>Kaa na Maji:</strong> Kunywa maji ya kutosha kila siku, kulingana na uzito wako na kiwango cha shughuli. <a href="https://www.who.int/news-room/fact-sheets/detail/drinking-water" target="_blank">Jifunze zaidi</a>.</li>
                    <li><strong>Chakula Bora:</strong> Jumuisha aina mbalimbali za vyakula vyenye virutubisho kama matunda, mboga, na protini zisizo na mafuta. <a href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" target="_blank">Jifunze zaidi</a>.</li>
                    <li><strong>Mazoezi ya Mara kwa Mara:</strong> Lenga angalau dakika 150 za shughuli za wastani kwa wiki. <a href="https://www.cdc.gov/physical-activity-basics/index.html" target="_blank">Jifunze zaidi</a>.</li>
                    <li><strong>Usingizi wa Kutosha:</strong> Weka kipaumbele kwa saa 7-9 za usingizi bora kila usiku. <a href="https://www.sleepfoundation.org/how-sleep-works" target="_blank">Jifunze zaidi</a>.</li>
                    <li><strong>Afya ya Akili:</strong> Fanya mazoezi ya kudhibiti msongo wa mawazo kupitia kuzingatia au mambo ya kupendeza. <a href="https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/mindfulness" target="_blank">Jifunze zaidi</a>.</li>
                </ul>
            """,
            "dialog_close": "Funga",
            "about_us_label": "Kuhusu Sisi",
            "about_us_content": "HealthBuddy imejitolea kutoa ushauri wa afya wa kibinafsi ili kukusaidia kuishi maisha ya afya.",
            "disclaimer_label": "Kanusho",
            "disclaimer_content": "Programu hii haiwezi kuchukua nafasi ya ushauri wa kitaalamu wa matibabu. Daima wasiliana na mtoa huduma za afya kwa masuala ya matibabu.",
            "copyright": "© 2025 HealthToTech. Haki zote zimehifadhiwa.",
            "error_weight": "Tafadhali ingiza uzito halali wa chanya.",
            "error_height": "Tafadhali ingiza urefu halali wa chanya.",
            "error_age": "Tafadhali ingiza umri halali wa chanya.",
            "error_email": "Tafadhali ingiza anwani halali ya barua pepe."
        }
    }
    t = translations.get(lang, translations["en"])

    if request.method == "POST":
        try:
            weight = float(request.form.get("weight"))
            height = float(request.form.get("height"))
            age = int(request.form.get("age"))
            gender = request.form.get("gender")
            activity_level = request.form.get("activity_level")
            email = request.form.get("email", "").strip()

            # Input validation
            if weight <= 0 or height <= 0 or age <= 0:
                flash(t["error_weight"] if weight <= 0 else t["error_height"] if height <= 0 else t["error_age"],
                      "error")
                return render_template_string(index_template, t=t, lang=lang)
            if gender not in ['male', 'female', 'other'] or activity_level not in ['low', 'moderate', 'high']:
                flash("Invalid gender or activity level.", "error")
                return render_template_string(index_template, t=t, lang=lang)
            if email and not email.endswith(('.com', '.org', '.net', '.edu')):
                flash(t["error_email"], "error")
                return render_template_string(index_template, t=t, lang=lang)

            water_intake = calculate_water_intake(weight, activity_level)
            health_tips = generate_health_tips(age, gender, weight, height, activity_level, lang)

            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute('''
                    INSERT INTO health_records (weight, height, age, gender, activity_level, water_intake, health_tips, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (weight, height, age, gender, activity_level, water_intake, ';'.join(health_tips),
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                logger.info("Health record saved successfully")

            result = {
                "weight": weight,
                "height": height,
                "age": age,
                "gender": gender,
                "activity_level": activity_level,
                "water_intake": water_intake,
                "health_tips": health_tips,
                "bmi": calculate_bmi(weight, height)
            }

            if email:
                send_health_report(email, result, lang)
                flash("Health report sent to your email!", "success")

            return render_template_string(index_template, result=result, t=t, lang=lang)
        except ValueError:
            flash("Please enter valid numeric values for weight, height, and age.", "error")
        except Exception as e:
            logger.error(f"Error processing form: {e}")
            flash("An error occurred. Please try again.", "error")

    return render_template_string(index_template, t=t, lang=lang)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Handle admin login functionality."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
                user = c.fetchone()
                if user and check_password_hash(user[0], password):
                    session['admin'] = True
                    session.permanent = True
                    flash("Login successful!", "success")
                    return redirect(url_for('admin_dashboard'))
                flash("Invalid username or password.", "error")
        except sqlite3.Error as e:
            logger.error(f"Database error during login: {e}")
            flash("An error occurred. Please try again.", "error")

    return render_template_string(admin_login_template)


@app.route("/admin/dashboard", methods=["GET", "POST"])
def admin_dashboard():
    """Display admin dashboard with health records and statistics."""
    if not session.get('admin'):
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for('admin_login'))

    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            query = "SELECT * FROM health_records WHERE 1=1"
            params = []
            date_filter = request.form.get("date_filter", "")
            gender_filter = request.form.get("gender_filter", "")
            activity_filter = request.form.get("activity_filter", "")

            if date_filter:
                query += " AND date(timestamp) = ?"
                params.append(date_filter)
            if gender_filter:
                query += " AND gender = ?"
                params.append(gender_filter)
            if activity_filter:
                query += " AND activity_level = ?"
                params.append(activity_filter)

            c.execute(query, params)
            records = [dict(row) for row in c.fetchall()]

            c.execute(
                "SELECT AVG(weight / ((height / 100) * (height / 100))) as avg_bmi, AVG(water_intake) as avg_water FROM health_records")
            stats = c.fetchone()
            avg_bmi = round(stats['avg_bmi'], 2) if stats['avg_bmi'] else 0
            avg_water = round(stats['avg_water'], 2) if stats['avg_water'] else 0

            c.execute("""
                SELECT 
                    SUM(CASE WHEN weight / ((height / 100) * (height / 100)) < 18.5 THEN 1 ELSE 0 END) as underweight,
                    SUM(CASE WHEN weight / ((height / 100) * (height / 100)) BETWEEN 18.5 AND 24.9 THEN 1 ELSE 0 END) as healthy,
                    SUM(CASE WHEN weight / ((height / 100) * (height / 100)) BETWEEN 25 AND 29.9 THEN 1 ELSE 0 END) as overweight,
                    SUM(CASE WHEN weight / ((height / 100) * (height / 100)) >= 30 THEN 1 ELSE 0 END) as obese
                FROM health_records
            """)
            bmi_dist = c.fetchone()

        return render_template_string(admin_dashboard_template, records=records, bmi_dist=bmi_dist,
                                      avg_bmi=avg_bmi, avg_water=avg_water)
    except sqlite3.Error as e:
        logger.error(f"Database error in dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "error")
        return redirect(url_for('admin_login'))


@app.route("/admin/logout")
def admin_logout():
    """Handle admin logout."""
    session.pop('admin', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))


@app.route("/admin/export_csv")
def export_csv():
    """Export health records to CSV."""
    if not session.get('admin'):
        flash("Please log in to export data.", "error")
        return redirect(url_for('admin_login'))

    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM health_records")
            records = c.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ['ID', 'Weight (kg)', 'Height (cm)', 'Age', 'Gender', 'Activity Level', 'Water Intake (L)', 'BMI',
             'Health Tips', 'Timestamp'])
        for record in records:
            bmi = calculate_bmi(record['weight'], record['height'])
            writer.writerow([
                record['id'], record['weight'], record['height'], record['age'],
                record['gender'], record['activity_level'], record['water_intake'],
                round(bmi, 2), record['health_tips'], record['timestamp']
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='healthbuddy_records.csv'
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        flash("An error occurred while exporting the data.", "error")
        return redirect(url_for('admin_dashboard'))


# Index template
index_template = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t['title'] }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Poppins', sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #e0f7fa 0%, #c8e6c9 100%);
            color: #333;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        h1 {
            text-align: center;
            color: #1b5e20;
            font-size: clamp(2em, 5vw, 2.5em);
            margin-bottom: 20px;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .intro {
            text-align: center;
            font-size: clamp(1em, 3vw, 1.2em);
            color: #424242;
            margin-bottom: 20px;
        }
        .lang-switch {
            text-align: center;
            margin-bottom: 20px;
        }
        .lang-switch a {
            margin: 0 10px;
            color: #2e7d32;
            text-decoration: none;
            font-weight: 600;
        }
        .lang-switch a:hover {
            text-decoration: underline;
        }
        .container {
            background: #ffffff;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            margin-bottom: 30px;
            transition: transform 0.3s ease;
        }
        .container:hover {
            transform: translateY(-5px);
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #2e7d32;
        }
        input, select {
            width: 100%;
            padding: 12px;
            border: 1px solid #81c784;
            border-radius: 6px;
            font-size: 1em;
            background-color: #f1f8e9;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #2e7d32;
            box-shadow: 0 0 8px rgba(46, 125, 50, 0.3);
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(to right, #4CAF50, #2e7d32);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: clamp(1em, 3vw, 1.2em);
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s, transform 0.2s;
        }
        button:hover {
            background: linear-gradient(to right, #45a049, #27632a);
            transform: scale(1.02);
        }
        .error {
            color: #d81b60;
            text-align: center;
            margin-bottom: 15px;
            background: #fce4ec;
            padding: 10px;
            border-radius: 6px;
        }
        .success {
            color: #2e7d32;
            text-align: center;
            margin-bottom: 15px;
            background: #e8f5e9;
            padding: 10px;
            border-radius: 6px;
        }
        .result {
            background: #ffffff;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            display: {% if result %}block{% else %}none{% endif %};
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .result h3 {
            color: #1b5e20;
            font-size: clamp(1.5em, 4vw, 1.8em);
            margin-bottom: 15px;
        }
        .result p {
            margin-bottom: 12px;
            font-size: clamp(0.9em, 2.5vw, 1.1em);
            color: #424242;
        }
        .result ul {
            list-style-type: none;
            padding: 0;
            margin-bottom: 15px;
        }
        .result li {
            margin-bottom: 10px;
            font-size: clamp(0.9em, 2.5vw, 1em);
            padding: 10px;
            background: #e8f5e9;
            border-radius: 6px;
            position: relative;
            padding-left: 30px;
        }
        .result li::before {
            content: '✔';
            color: #2e7d32;
            position: absolute;
            left: 10px;
            font-size: 1.2em;
        }
        footer {
            margin-top: auto;
            padding: 20px;
            background: #1b5e20;
            color: white;
            text-align: center;
            border-radius: 8px;
            font-size: clamp(0.8em, 2vw, 0.9em);
        }
        footer a {
            color: #a5d6a7;
            text-decoration: none;
        }
        footer a:hover {
            text-decoration: underline;
        }
        .dialog {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .dialog-content {
            background: #ffffff;
            padding: 20px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            animation: slideIn 0.3s ease;
        }
        @keyframes slideIn {
            from { transform: scale(0.8); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .dialog-content h3 {
            color: #1b5e20;
            margin-bottom: 15px;
        }
        .dialog-content p, .dialog-content ul {
            margin-bottom: 15px;
            color: #424242;
        }
        .dialog-content a {
            color: #0288d1;
            text-decoration: none;
        }
        .dialog-content a:hover {
            text-decoration: underline;
        }
        .dialog-content button {
            background: #4CAF50;
            padding: 10px;
            width: auto;
            display: block;
            margin: 0 auto;
        }
        .health-tips-btn {
            margin: 10px auto;
            display: block;
            width: fit-content;
            background: #0288d1;
            padding: 10px 20px;
        }
        .health-tips-btn:hover {
            background: #0277bd;
        }
        @media (max-width: 600px) {
            body {
                padding: 10px;
            }
            h1 {
                font-size: 1.8em;
            }
            .container, .result, .dialog-content {
                padding: 15px;
            }
            button {
                font-size: 1em;
            }
            footer {
                padding: 15px;
            }
        }
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    </style>
    <script>
        function validateForm() {
            const weight = document.getElementById('weight').value;
            const height = document.getElementById('height').value;
            const age = document.getElementById('age').value;
            const email = document.getElementById('email').value;
            const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
            const lang = '{{ lang }}';
            const translations = {
                'en': {
                    'error_weight': 'Please enter a valid positive weight.',
                    'error_height': 'Please enter a valid positive height.',
                    'error_age': 'Please enter a valid positive age.',
                    'error_email': 'Please enter a valid email address.'
                },
                'sw': {
                    'error_weight': 'Tafadhali ingiza uzito halali wa chanya.',
                    'error_height': 'Tafadhali ingiza urefu halali wa chanya.',
                    'error_age': 'Tafadhali ingiza umri halali wa chanya.',
                    'error_email': 'Tafadhali ingiza anwani halali ya barua pepe.'
                }
            };
            let error = '';
            if (isNaN(weight) || weight <= 0) {
                error = translations[lang]['error_weight'];
            } else if (isNaN(height) || height <= 0) {
                error = translations[lang]['error_height'];
            } else if (isNaN(age) || age <= 0) {
                error = translations[lang]['error_age'];
            } else if (email && !emailRegex.test(email)) {
                error = translations[lang]['error_email'];
            }
            if (error) {
                document.getElementById('error').innerText = error;
                document.getElementById('error').style.display = 'block';
                return false;
            }
            return true;
        }
        function openDialog() {
            document.getElementById('healthDialog').style.display = 'flex';
        }
        function closeDialog() {
            document.getElementById('healthDialog').style.display = 'none';
        }
    </script>
</head>
<body>
    <h1>{{ t['title'] }}</h1>
    <p class="intro">{{ t['intro'] }}</p>
    <div class="lang-switch">
        <a href="?lang=en">English</a> | <a href="?lang=sw">Swahili</a>
    </div>
    <button class="health-tips-btn" onclick="openDialog()">{{ t['learn_health'] }}</button>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ category }}" id="error">{{ message }}</p>
                {% endfor %}
            {% else %}
                <p class="error" id="error" style="display: none;"></p>
            {% endif %}
        {% endwith %}
        <form method="POST" onsubmit="return validateForm()">
            <div class="form-group">
                <label for="weight">{{ t['weight_label'] }}</label>
                <input type="number" id="weight" name="weight" step="0.1" required placeholder="e.g., 70.5">
            </div>
            <div class="form-group">
                <label for="height">{{ t['height_label'] }}</label>
                <input type="number" id="height" name="height" step="0.1" required placeholder="e.g., 170">
            </div>
            <div class="form-group">
                <label for="age">{{ t['age_label'] }}</label>
                <input type="number" id="age" name="age" required placeholder="e.g., 30">
            </div>
            <div class="form-group">
                <label for="gender">{{ t['gender_label'] }}</label>
                <select id="gender" name="gender" required>
                    <option value="" disabled selected>{{ t['select_gender'] }}</option>
                    <option value="male">{{ t['male'] }}</option>
                    <option value="female">{{ t['female'] }}</option>
                    <option value="other">{{ t['other'] }}</option>
                </select>
            </div>
            <div class="form-group">
                <label for="activity_level">{{ t['activity_label'] }}</label>
                <select id="activity_level" name="activity_level" required>
                    <option value="" disabled selected>{{ t['select_activity'] }}</option>
                    <option value="low">{{ t['low'] }}</option>
                    <option value="moderate">{{ t['moderate'] }}</option>
                    <option value="high">{{ t['high'] }}</option>
                </select>
            </div>
            <div class="form-group">
                <label for="email">{{ t['email_label'] }}</label>
                <input type="email" id="email" name="email" placeholder="e.g., user@example.com">
            </div>
            <button type="submit">{{ t['submit'] }}</button>
        </form>
    </div>
    {% if result %}
        <div class="result">
            <h3>{{ t['report_title'] }}</h3>
            <p><strong>{{ t['weight_label'][:-1] }}</strong> {{ result.weight }} kg</p>
            <p><strong>{{ t['height_label'][:-1] }}</strong> {{ result.height }} cm</p>
            <p><strong>{{ t['age_label'][:-1] }}</strong> {{ result.age }}</p>
            <p><strong>{{ t['gender_label'][:-1] }}</strong> {{ result.gender | capitalize }}</p>
            <p><strong>{{ t['activity_label'][:-1] }}</strong> {{ result.activity_level | capitalize }}</p>
            <p><strong>{{ t['bmi_label'] }}</strong> {{ result.bmi }}</p>
            <h3>{{ t['water_intake_title'] }}</h3>
            <p>{{ result.water_intake }} liters</p>
            <h3>{{ t['health_tips_title'] }}</h3>
            <ul>
                {% for tip in result.health_tips %}
                    <li>{{ tip }}</li>
                {% endfor %}
            </ul>
        </div>
    {% endif %}
    <div class="dialog" id="healthDialog">
        <div class="dialog-content">
            <h3>{{ t['dialog_title'] }}</h3>
            {{ t['dialog_content'] | safe }}
            <button onclick="closeDialog()">{{ t['dialog_close'] }}</button>
        </div>
    </div>
    <footer>
        <p><strong>{{ t['about_us_label'] }}:</strong> {{ t['about_us_content'] }}</p>
        <p><strong>{{ t['disclaimer_label'] }}:</strong> {{ t['disclaimer_content'] }}</p>
        <p>{{ t['copyright'] }}</p>
    </footer>
</body>
</html>
"""

# Admin login template
admin_login_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HealthBuddy Admin Login</title>
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            max-width: 400px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #e0f7fa 0%, #c8e6c9 100%);
            color: #333;
        }
        h1 {
            text-align: center;
            color: #1b5e20;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #2e7d32;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #81c784;
            border-radius: 6px;
            font-size: 1em;
            background-color: #f1f8e9;
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(to right, #4CAF50, #2e7d32);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 1.2em;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: linear-gradient(to right, #45a049, #27632a);
        }
        .error {
            color: #d81b60;
            text-align: center;
            margin-bottom: 15px;
            background: #fce4ec;
            padding: 10px;
            border-radius: 6px;
        }
        .success {
            color: #2e7d32;
            text-align: center;
            margin-bottom: 15px;
            background: #e8f5e9;
            padding: 10px;
            border-radius: 6px;
        }
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    </style>
</head>
<body>
    <h1>Admin Login</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <p class="{{ category }}">{{ message }}</p>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form method="POST">
        <div class="form-group">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
        </div>
        <div class="form-group">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>
"""

# Admin dashboard template
admin_dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HealthBuddy Admin Dashboard</title>
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #e0f7fa 0%, #c8e6c9 100%);
            color: #333;
        }
        h1 {
            text-align: center;
            color: #1b5e20;
            margin-bottom: 20px;
        }
        .filter-form {
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .filter-form div {
            flex: 1;
            min-width: 200px;
        }
        label {
            font-weight: 600;
            color: #2e7d32;
            display: block;
            margin-bottom: 5px;
        }
        input, select, button {
            width: 100%;
            padding: 10px;
            margin-top: 5px;
            border: 1px solid #81c784;
            border-radius: 6px;
            font-size: 1em;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #45a049;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #2e7d32;
            color: white;
        }
        tr:nth-child(even) {
            background: #f1f8e9;
        }
        .charts {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 20px;
        }
        canvas {
            max-width: 100%;
            flex: 1;
            min-width: 300px;
        }
        .logout-link, .export-link {
            display: inline-block;
            margin: 10px 0;
            color: #2e7d32;
            text-decoration: none;
            font-weight: 600;
        }
        .logout-link:hover, .export-link:hover {
            text-decoration: underline;
        }
        .error {
            color: #d81b60;
            text-align: center;
            margin-bottom: 15px;
            background: #fce4ec;
            padding: 10px;
            border-radius: 6px;
        }
        .success {
            color: #2e7d32;
            text-align: center;
            margin-bottom: 15px;
            background: #e8f5e9;
            padding: 10px;
            border-radius: 6px;
        }
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>HealthBuddy Admin Dashboard</h1>
    <p><a class="logout-link" href="{{ url_for('admin_logout') }}">Logout</a></p>
    <p><a class="export-link" href="{{ url_for('export_csv') }}">Export to CSV</a></p>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <p class="{{ category }}">{{ message }}</p>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form class="filter-form" method="POST">
        <div>
            <label for="date_filter">Filter by Date:</label>
            <input type="date" id="date_filter" name="date_filter">
        </div>
        <div>
            <label for="gender_filter">Filter by Gender:</label>
            <select id="gender_filter" name="gender_filter">
                <option value="">All</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
            </select>
        </div>
        <div>
            <label for="activity_filter">Filter by Activity Level:</label>
            <select id="activity_filter" name="activity_filter">
                <option value="">All</option>
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
            </select>
        </div>
        <button type="submit">Apply Filters</button>
    </form>
    <table>
        <tr>
            <th>ID</th>
            <th>Weight (kg)</th>
            <th>Height (cm)</th>
            <th>Age</th>
            <th>Gender</th>
            <th>Activity Level</th>
            <th>Water Intake (L)</th>
            <th>BMI</th>
            <th>Timestamp</th>
        </tr>
        {% for record in records %}
            <tr>
                <td>{{ record['id'] }}</td>
                <td>{{ record['weight'] }}</td>
                <td>{{ record['height'] }}</td>
                <td>{{ record['age'] }}</td>
                <td>{{ record['gender'] | capitalize }}</td>
                <td>{{ record['activity_level'] | capitalize }}</td>
                <td>{{ record['water_intake'] }}</td>
                <td>{{ "%.2f" | format(record['weight'] / ((record['height'] / 100) * (record['height'] / 100))) }}</td>
                <td>{{ record['timestamp'] }}</td>
            </tr>
        {% endfor %}
    </table>
    <div class="charts">
        <div>
            <canvas id="bmiChart"></canvas>
        </div>
        <div>
            <canvas id="statsChart"></canvas>
        </div>
    </div>
    <script>
        const bmiCtx = document.getElementById('bmiChart').getContext('2d');
        new Chart(bmiCtx, {
            type: 'pie',
            data: {
                labels: ['Underweight', 'Healthy', 'Overweight', 'Obese'],
                datasets: [{
                    data: [{{ bmi_dist['underweight'] or 0 }}, {{ bmi_dist['healthy'] or 0 }}, {{ bmi_dist['overweight'] or 0 }}, {{ bmi_dist['obese'] or 0 }}],
                    backgroundColor: ['#ff6384', '#36a2eb', '#ffcd56', '#4bc0c0']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'BMI Distribution' }
                }
            }
        });
        const statsCtx = document.getElementById('statsChart').getContext('2d');
        new Chart(statsCtx, {
            type: 'bar',
            data: {
                labels: ['Average BMI', 'Average Water Intake (L)'],
                datasets: [{
                    label: 'Statistics',
                    data: [{{ avg_bmi }}, {{ avg_water }}],
                    backgroundColor: ['#36a2eb', '#4bc0c0']
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: { title: { display: true, text: 'Health Statistics' } }
            }
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))