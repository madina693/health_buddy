import os
import io
import csv
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Database configuration
DATABASE = 'healthbuddy.db'

# Global translations dictionary
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
        "chronic_diseases_label": "Chronic Diseases:",
        "sleep_hours_label": "Hours of Sleep per Night:",
        "sleep_consistency_label": "Regular Bedtime?:",
        "sleep_disturbances_label": "Sleep Disturbances:",
        "substance_use_label": "Substance Use (e.g., alcohol, tobacco):",
        "menstrual_regularity_label": "Menstrual Cycle Regularity:",
        "pregnancy_history_label": "Pregnancy History:",
        "contraceptive_use_label": "Contraceptive Use:",
        "submit": "Get Your Health Advice",
        "select_gender": "Select gender",
        "select_activity": "Select activity level",
        "male": "Male",
        "female": "Female",
        "low": "Low (sedentary)",
        "moderate": "Moderate (light exercise)",
        "high": "High (active, regular exercise)",
        "yes": "Yes",
        "no": "No",
        "regular": "Regular",
        "irregular": "Irregular",
        "none": "None",
        "insomnia": "Insomnia",
        "waking_tired": "Waking up tired",
        "has_pregnancy": "Yes, previous pregnancies",
        "no_pregnancy": "No pregnancies",
        "contraceptive_none": "None",
        "contraceptive_pill": "Pill",
        "contraceptive_iud": "IUD",
        "report_title": "Your Personalized Health Report",
        "water_intake_title": "Recommended Daily Water Intake",
        "health_tips_title": "Personalized Health Tips",
        "bmi_label": "BMI:",
        "dialog_title": "Healthy Living Tips",
        "dialog_content": """
            Adopting a healthy lifestyle can significantly improve your well-being. Here are some key tips:
            <ul>
                <li><strong>Stay Hydrated:</strong> Drink adequate water daily based on your weight and activity level. <a href="https://www.who.int/news-room/fact-sheets/detail/drinking-water" target="_blank">Learn more</a>.</li>
                <li><strong>Balanced Diet:</strong> Include nutrient-rich foods like fruits, vegetables, whole grains, and lean proteins. <a href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" target="_blank">Learn more</a>.</li>
                <li><strong>Regular Exercise:</strong> Aim for at least 150 minutes of moderate activity weekly to boost physical health. <a href="https://www.cdc.gov/physical-activity-basics/index.html" target="_blank">Learn more</a>.</li>
                <li><strong>Adequate Sleep:</strong> Prioritize 7-9 hours of quality sleep nightly to support recovery and mental clarity. <a href="https://www.sleepfoundation.org/how-sleep-works" target="_blank">Learn more</a>.</li>
                <li><strong>Mental Health:</strong> Practice mindfulness, meditation, or hobbies to manage stress effectively. <a href="https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/mindfulness" target="_blank">Learn more</a>.</li>
                <li><strong>Chronic Disease Management:</strong> Regular check-ups and adherence to medical advice are crucial for managing conditions like diabetes or hypertension. <a href="https://www.cdc.gov/chronic-disease/index.html" target="_blank">Learn more</a>.</li>
                <li><strong>Substance Avoidance:</strong> Limit or avoid alcohol and tobacco to reduce health risks. <a href="https://www.who.int/news-room/fact-sheets/detail/tobacco" target="_blank">Learn more</a>.</li>
                <li><strong>Reproductive Health:</strong> For women, regular gynecological check-ups can help monitor menstrual and reproductive health. <a href="https://www.womenshealth.gov/" target="_blank">Learn more</a>.</li>
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
        "error_sleep_hours": "Please enter valid sleep hours (0-24).",
        "error_gender": "Please select a valid gender.",
        "error_activity": "Please select a valid activity level.",
        "error_invalid_input": "Please select a valid option for {field}.",
        "bmi_underweight": "Your BMI suggests you may be underweight. Consider consulting a nutritionist to ensure adequate nutrient intake.",
        "bmi_healthy": "Your BMI is in the healthy range. Maintain a balanced diet and regular exercise to stay on track.",
        "bmi_overweight": "Your BMI indicates you may be overweight. Increase physical activity and consider a balanced diet plan.",
        "bmi_obese": "Your BMI suggests obesity. Consult a healthcare professional for personalized advice and support.",
        "activity_low": "Aim for at least 150 minutes of moderate exercise per week to improve overall health.",
        "activity_moderate": "Great job staying moderately active! Incorporate strength training 2-3 times per week for added benefits.",
        "activity_high": "You're highly active! Ensure proper recovery with adequate sleep and hydration to support your routine.",
        "sleep_poor": "Poor sleep quality can affect your health. Aim for 7-9 hours of consistent sleep and consider a sleep specialist if disturbances persist.",
        "sleep_good": "Good sleep habits support overall health. Maintain consistent sleep schedules for optimal well-being.",
        "chronic_disease_yes": "Managing chronic conditions requires regular check-ups and adherence to medical advice.",
        "chronic_disease_no": "No chronic conditions reported. Continue regular health check-ups to maintain your well-being.",
        "substance_use_yes": "Substance use can impact your health. Consider consulting a professional for support and guidance.",
        "substance_use_no": "Avoiding substance use is beneficial for long-term health. Keep up the healthy choices!",
        "menstrual_irregular": "Irregular menstrual cycles may require medical evaluation. Consult a gynecologist for further assessment.",
        "menstrual_regular": "Regular menstrual cycles are a good sign of hormonal health. Continue monitoring any changes.",
        "pregnancy_history": "Previous pregnancies may influence health needs. Discuss with your doctor for tailored advice.",
        "contraceptive_use": "Contraceptive use should be discussed with a healthcare provider to ensure it meets your health needs.",
        "general_nutrition": "Incorporate nutrient-dense foods like leafy greens, nuts, and lean proteins to support overall health.",
        "mental_health": "Practice stress-reduction techniques like meditation or yoga to enhance mental well-being.",
        "hydration": "Staying hydrated is key to energy levels and organ function. Carry a water bottle to track intake."
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
        "chronic_diseases_label": "Magonjwa ya Muda Mrefu:",
        "sleep_hours_label": "Saa za Kulala kwa Usiku:",
        "sleep_consistency_label": "Wakati wa Kulala wa Mara kwa Mara?:",
        "sleep_disturbances_label": "Usumbufu wa Usingizi:",
        "substance_use_label": "Matumizi ya Dawa (k.m., pombe, tumbaku):",
        "menstrual_regularity_label": "Uratibu wa Mizunguko ya Hedhi:",
        "pregnancy_history_label": "Historia ya Ujauzito:",
        "contraceptive_use_label": "Matumizi ya Uzazi wa Mpango:",
        "submit": "Pata Ushauri Wako wa Afya",
        "select_gender": "Chagua jinsia",
        "select_activity": "Chagua kiwango cha shughuli",
        "male": "Mwanaume",
        "female": "Mwanamke",
        "low": "Chini (kukaa tu)",
        "moderate": "Wastani (mazoezi mepesi)",
        "high": "Juu (shughuli za mara kwa mara)",
        "yes": "Ndiyo",
        "no": "Hapana",
        "regular": "Mara kwa mara",
        "irregular": "Sio ya mara kwa mara",
        "none": "Hakuna",
        "insomnia": "Kukosa usingizi",
        "waking_tired": "Kuamka ukiwa umechoka",
        "has_pregnancy": "Ndiyo, mimba za awali",
        "no_pregnancy": "Hapana mimba",
        "contraceptive_none": "Hakuna",
        "contraceptive_pill": "Vidonge",
        "contraceptive_iud": "IUD",
        "report_title": "Ripoti Yako ya Afya ya Kibinafsi",
        "water_intake_title": "Ulaji wa Maji wa Kila Siku Unaopendekezwa",
        "health_tips_title": "Vidokezo vya Afya vya Kibinafsi",
        "bmi_label": "BMI:",
        "dialog_title": "Vidokezo vya Maisha ya Afya",
        "dialog_content": """
            Kuchukua mtindo wa maisha ya afya kunaweza kuboresha ustawi wako kwa kiasi kikubwa. Hapa kuna vidokezo vya msingi:
            <ul>
                <li><strong>Kaa na Maji:</strong> Kunywa maji ya kutosha kila siku kulingana na uzito wako na kiwango cha shughuli. <a href="https://www.who.int/news-room/fact-sheets/detail/drinking-water" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Chakula Bora:</strong> Jumuisha vyakula vyenye virutubisho kama matunda, mboga, nafaka za jumla, na protini zisizo na mafuta. <a href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Mazoezi ya Mara kwa Mara:</strong> Lenga angalau dakika 150 za shughuli za wastani kwa wiki ili kuimarisha afya ya mwili. <a href="https://www.cdc.gov/physical-activity-basics/index.html" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Usingizi wa Kutosha:</strong> Weka kipaumbele kwa saa 7-9 za usingizi bora kila usiku kwa ajili ya kupona na uwazi wa akili. <a href="https://www.sleepfoundation.org/how-sleep-works" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Afya ya Akili:</strong> Fanya mazoezi ya kuzingatia, kutafakari, au mambo ya kupendeza ili kudhibiti msongo wa mawazo kwa ufanisi. <a href="https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/mindfulness" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Kudhibiti Magonjwa ya Muda Mrefu:</strong> Uchunguzi wa mara kwa mara na kufuata ushauri wa matibabu ni muhimu kwa kudhibiti hali kama kisukari au shinikizo la damu. <a href="https://www.cdc.gov/chronic-disease/index.html" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Kuepuka Dawa:</strong> Punguza au epuka pombe na tumbaku ili kupunguza hatari za afya. <a href="https://www.who.int/news-room/fact-sheets/detail/tobacco" target="_blank">Jifunze zaidi</a>.</li>
                <li><strong>Afya ya Uzazi:</strong> Kwa wanawake, uchunguzi wa mara kwa mara wa magonjwa ya wanawake unaweza kusaidia kufuatilia afya ya hedhi na uzazi. <a href="https://www.womenshealth.gov/" target="_blank">Jifunze zaidi</a>.</li>
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
        "error_sleep_hours": "Tafadhali ingiza saa za kulala zinazofaa (0-24).",
        "error_gender": "Tafadhali chagua jinsia halali.",
        "error_activity": "Tafadhali chagua kiwango cha shughuli halali.",
        "error_invalid_input": "Tafadhali chagua chaguo halali kwa {field}.",
        "bmi_underweight": "BMI yako inaonyesha unaweza kuwa na uzito wa chini. Fikiria kushauriana na mtaalamu wa lishe.",
        "bmi_healthy": "BMI yako iko katika kiwango cha afya. Endelea kudumisha chakula bora na mazoezi ya mara kwa mara.",
        "bmi_overweight": "BMI yako inaonyesha unaweza kuwa na uzito wa ziada. Ongeza shughuli za kimwili na fuata chakula bora.",
        "bmi_obese": "BMI yako inaonyesha unene. Shauriana na mtaalamu wa afya kwa ushauri wa kibinafsi.",
        "activity_low": "Lenga angalau dakika 150 za mazoezi ya wastani kwa wiki ili kuboresha afya ya jumla.",
        "activity_moderate": "Kazi nzuri kwa kuendelea na shughuli za wastani! Jumuisha mafunzo ya nguvu mara 2-3 kwa wiki.",
        "activity_high": "Wewe ni mwenye shughuli za juu! Hakikisha unapata nafuu ya kutosha na usingizi wa kutosha na maji.",
        "sleep_poor": "Ubora duni wa usingizi unaweza kuathiri afya yako. Lenga kulala saa 7-9 za mara kwa mara na fikiria mtaalamu wa usingizi ikiwa usumbufu utaendelea.",
        "sleep_good": "Tabia nzuri za kulala zinasaidia afya ya jumla. Dumisha ratiba za kulala za mara kwa mara kwa ustawi bora.",
        "chronic_disease_yes": "Kudhibiti hali za muda mrefu kunahitaji uchunguzi wa mara kwa mara na kufuata ushauri wa matibabu.",
        "chronic_disease_no": "Hakuna hali za muda mrefu zilizoripotiwa. Endelea na uchunguzi wa afya wa mara kwa mara ili kudumisha ustawi wako.",
        "substance_use_yes": "Matumizi ya dawa za kulevya yanaweza kuathiri afya yako. Fikiria kushauriana na mtaalamu kwa msaada na mwongozo.",
        "substance_use_no": "Kuepuka matumizi ya dawa za kulevya ni faida kwa afya ya muda mrefu. Endelea na chaguo za afya!",
        "menstrual_irregular": "Mizunguko ya hedhi isiyo ya kawaida inaweza kuhitaji tathmini ya matibabu. Shauriana na daktari wa wanawake kwa tathmini zaidi.",
        "menstrual_regular": "Mizunguko ya hedhi ya kawaida ni ishara nzuri ya afya ya homoni. Endelea kufuatilia mabadiliko yoyote.",
        "pregnancy_history": "Historia ya ujauzito inaweza kuathiri mahitaji ya afya. Jadiliana na daktari wako kwa ushauri wa kibinafsi.",
        "contraceptive_use": "Matumizi ya uzazi wa mpango yanapaswa kujadiliwa na mtoa huduma za afya ili kuhakikisha yanakidhi mahitaji yako ya afya.",
        "general_nutrition": "Jumuisha vyakula vyenye virutubisho vingi kama mboga za majani, karanga, na protini zisizo na mafuta ili kusaidia afya ya jumla.",
        "mental_health": "Fanya mazoezi ya kupunguza msongo wa mawazo kama kutafakari au yoga ili kuboresha ustawi wa akili.",
        "hydration": "Kukaa na maji ni muhimu kwa viwango vya nishati na utendaji wa viungo. Beba chupa ya maji ili kufuatilia ulaji."
    }
}

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
                    chronic_diseases TEXT NOT NULL,
                    sleep_hours REAL NOT NULL,
                    sleep_consistency TEXT NOT NULL,
                    sleep_disturbances TEXT NOT NULL,
                    substance_use TEXT NOT NULL,
                    menstrual_regularity TEXT,
                    pregnancy_history TEXT,
                    contraceptive_use TEXT,
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
            c.execute("SELECT * FROM users WHERE username = 'admin'")
            if not c.fetchone():
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                         ('admin', generate_password_hash('admin123')))
            conn.commit()
            logger.info("Database initialized successfully")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        raise

def calculate_water_intake(weight, activity_level):
    """Calculate recommended daily water intake based on weight and activity level."""
    base_ml_per_kg = 30
    activity_multipliers = {'high': 5, 'moderate': 2.5, 'low': 0}
    water_ml = weight * (base_ml_per_kg + activity_multipliers.get(activity_level, 0))
    return round(water_ml / 1000, 2)

def calculate_bmi(weight, height):
    """Calculate BMI based on weight and height."""
    return round(weight / ((height / 100) ** 2), 2)

def generate_health_tips(age, gender, weight, height, activity_level, chronic_diseases, sleep_hours, sleep_consistency, sleep_disturbances, substance_use, menstrual_regularity, pregnancy_history, contraceptive_use, lang="en"):
    """Generate personalized health tips based on user input."""
    bmi = calculate_bmi(weight, height)
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
    if sleep_hours < 7 or sleep_consistency == 'no' or sleep_disturbances != 'none':
        tips.append(t["sleep_poor"])
    else:
        tips.append(t["sleep_good"])
    tips.append(t[f"chronic_disease_{chronic_diseases.lower()}"])
    tips.append(t[f"substance_use_{substance_use.lower()}"])
    if gender == 'female' and menstrual_regularity:
        tips.append(t[f"menstrual_{menstrual_regularity.lower()}"])
    if gender == 'female' and pregnancy_history == 'has_pregnancy':
        tips.append(t["pregnancy_history"])
    if gender == 'female' and contraceptive_use != 'none':
        tips.append(t["contraceptive_use"])
    tips.extend([t["general_nutrition"], t["mental_health"], t["hydration"]])
    return tips

@app.route("/", methods=["GET", "POST"])
def index():
    """Handle main page with health form and results."""
    lang = request.args.get('lang', 'en')
    if lang not in ['en', 'sw']:
        lang = 'en'  # Default to English if invalid language
    try:
        init_db()
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        flash("Database error. Please try again later.", "error")
        return render_template_string(index_template, t=translations["en"], lang='en')

    t = translations.get(lang, translations["en"])

    if request.method == "POST":
        try:
            weight = request.form.get("weight")
            height = request.form.get("height")
            age = request.form.get("age")
            gender = request.form.get("gender")
            activity_level = request.form.get("activity_level")
            chronic_diseases = request.form.get("chronic_diseases", "no")
            sleep_hours = request.form.get("sleep_hours", "0")
            sleep_consistency = request.form.get("sleep_consistency", "no")
            sleep_disturbances = request.form.get("sleep_disturbances", "none")
            substance_use = request.form.get("substance_use", "no")
            menstrual_regularity = request.form.get("menstrual_regularity", None) if gender == "female" else None
            pregnancy_history = request.form.get("pregnancy_history", None) if gender == "female" else None
            contraceptive_use = request.form.get("contraceptive_use", None) if gender == "female" else None

            # Convert and validate numeric inputs
            try:
                weight = float(weight)
                height = float(height)
                age = int(age)
                sleep_hours = float(sleep_hours)
            except (ValueError, TypeError):
                flash("Please enter valid numeric values for weight, height, age, and sleep hours.", "error")
                return render_template_string(index_template, t=t, lang=lang)

            # Server-side validation
            if weight <= 0:
                flash(t["error_weight"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if height <= 0:
                flash(t["error_height"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if age <= 0:
                flash(t["error_age"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if gender not in ['male', 'female']:
                flash(t["error_gender"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if activity_level not in ['low', 'moderate', 'high']:
                flash(t["error_activity"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if sleep_hours < 0 or sleep_hours > 24:
                flash(t["error_sleep_hours"], "error")
                return render_template_string(index_template, t=t, lang=lang)
            if chronic_diseases not in ['yes', 'no']:
                flash(t["error_invalid_input"].format(field="Chronic Diseases"), "error")
                return render_template_string(index_template, t=t, lang=lang)
            if sleep_consistency not in ['yes', 'no']:
                flash(t["error_invalid_input"].format(field="Sleep Consistency"), "error")
                return render_template_string(index_template, t=t, lang=lang)
            if sleep_disturbances not in ['none', 'insomnia', 'waking_tired']:
                flash(t["error_invalid_input"].format(field="Sleep Disturbances"), "error")
                return render_template_string(index_template, t=t, lang=lang)
            if substance_use not in ['yes', 'no']:
                flash(t["error_invalid_input"].format(field="Substance Use"), "error")
                return render_template_string(index_template, t=t, lang=lang)
            if gender == 'female':
                if menstrual_regularity and menstrual_regularity not in ['regular', 'irregular']:
                    flash(t["error_invalid_input"].format(field="Menstrual Regularity"), "error")
                    return render_template_string(index_template, t=t, lang=lang)
                if pregnancy_history and pregnancy_history not in ['has_pregnancy', 'no_pregnancy']:
                    flash(t["error_invalid_input"].format(field="Pregnancy History"), "error")
                    return render_template_string(index_template, t=t, lang=lang)
                if contraceptive_use and contraceptive_use not in ['none', 'pill', 'iud']:
                    flash(t["error_invalid_input"].format(field="Contraceptive Use"), "error")
                    return render_template_string(index_template, t=t, lang=lang)

            water_intake = calculate_water_intake(weight, activity_level)
            health_tips = generate_health_tips(age, gender, weight, height, activity_level, chronic_diseases, sleep_hours, sleep_consistency, sleep_disturbances, substance_use, menstrual_regularity, pregnancy_history, contraceptive_use, lang)

            try:
                with sqlite3.connect(DATABASE) as conn:
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO health_records (weight, height, age, gender, activity_level, water_intake, health_tips, chronic_diseases, sleep_hours, sleep_consistency, sleep_disturbances, substance_use, menstrual_regularity, pregnancy_history, contraceptive_use, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (weight, height, age, gender, activity_level, water_intake, ';'.join(health_tips), chronic_diseases, sleep_hours, sleep_consistency, sleep_disturbances, substance_use, menstrual_regularity, pregnancy_history, contraceptive_use, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    logger.info("Health record saved successfully")
            except sqlite3.Error as e:
                logger.error(f"Database error during record insertion: {e}. Data: weight={weight}, height={height}, age={age}, gender={gender}, activity_level={activity_level}, chronic_diseases={chronic_diseases}, sleep_hours={sleep_hours}, sleep_consistency={sleep_consistency}, sleep_disturbances={sleep_disturbances}, substance_use={substance_use}, menstrual_regularity={menstrual_regularity}, pregnancy_history={pregnancy_history}, contraceptive_use={contraceptive_use}")
                flash("Failed to save health record due to a database issue. Please try again.", "error")
                return render_template_string(index_template, t=t, lang=lang)

            result = {
                "weight": weight,
                "height": height,
                "age": age,
                "gender": gender,
                "activity_level": activity_level,
                "water_intake": water_intake,
                "health_tips": health_tips,
                "bmi": calculate_bmi(weight, height),
                "chronic_diseases": chronic_diseases,
                "sleep_hours": sleep_hours,
                "sleep_consistency": sleep_consistency,
                "sleep_disturbances": sleep_disturbances,
                "substance_use": substance_use,
                "menstrual_regularity": menstrual_regularity,
                "pregnancy_history": pregnancy_history,
                "contraceptive_use": contraceptive_use
            }

            return render_template_string(index_template, result=result, t=t, lang=lang)
        except Exception as e:
            logger.error(f"Unexpected error processing form: {e}")
            flash("An unexpected error occurred. Please try again.", "error")
            return render_template_string(index_template, t=t, lang=lang)

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
            flash("Database error during login. Please try again.", "error")

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
            if gender_filter in ['male', 'female']:
                query += " AND gender = ?"
                params.append(gender_filter)
            if activity_filter in ['low', 'moderate', 'high']:
                query += " AND activity_level = ?"
                params.append(activity_filter)

            c.execute(query, params)
            records = [dict(row) for row in c.fetchall()]

            c.execute(
                "SELECT AVG(weight / ((height / 100) * (height / 100))) as avg_bmi, AVG(water_intake) as avg_water, AVG(sleep_hours) as avg_sleep FROM health_records")
            stats = c.fetchone()
            avg_bmi = round(stats['avg_bmi'], 2) if stats['avg_bmi'] else 0
            avg_water = round(stats['avg_water'], 2) if stats['avg_water'] else 0
            avg_sleep = round(stats['avg_sleep'], 2) if stats['avg_sleep'] else 0

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
                                     avg_bmi=avg_bmi, avg_water=avg_water, avg_sleep=avg_sleep)
    except sqlite3.Error as e:
        logger.error(f"Database error in dashboard: {e}")
        flash("Database error while loading dashboard. Please try again.", "error")
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
             'Chronic Diseases', 'Sleep Hours', 'Sleep Consistency', 'Sleep Disturbances', 'Substance Use',
             'Menstrual Regularity', 'Pregnancy History', 'Contraceptive Use', 'Health Tips', 'Timestamp'])
        for record in records:
            bmi = calculate_bmi(record['weight'], record['height'])
            writer.writerow([
                record['id'], record['weight'], record['height'], record['age'],
                record['gender'], record['activity_level'], record['water_intake'],
                round(bmi, 2), record['chronic_diseases'], record['sleep_hours'],
                record['sleep_consistency'], record['sleep_disturbances'], record['substance_use'],
                record['menstrual_regularity'] or '', record['pregnancy_history'] or '', record['contraceptive_use'] or '',
                record['health_tips'], record['timestamp']
            ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='healthbuddy_records.csv'
        )
    except sqlite3.Error as e:
        logger.error(f"Database error exporting CSV: {e}")
        flash("Database error while exporting data. Please try again.", "error")
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        logger.error(f"Unexpected error exporting CSV: {e}")
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
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #81c784;
            border-radius: 6px;
            font-size: 1em;
            background-color: #f1f8e9;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        input:focus, select:focus, textarea:focus {
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
        #female-fields {
            display: none;
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
            const sleepHours = document.getElementById('sleep_hours').value;
            const gender = document.getElementById('gender').value;
            const activityLevel = document.getElementById('activity_level').value;
            const lang = '{{ lang }}';
            const translations = {
                'en': {
                    'error_weight': 'Please enter a valid positive weight.',
                    'error_height': 'Please enter a valid positive height.',
                    'error_age': 'Please enter a valid positive age.',
                    'error_sleep_hours': 'Please enter valid sleep hours (0-24).',
                    'error_gender': 'Please select a valid gender.',
                    'error_activity': 'Please select a valid activity level.'
                },
                'sw': {
                    'error_weight': 'Tafadhali ingiza uzito halali wa chanya.',
                    'error_height': 'Tafadhali ingiza urefu halali wa chanya.',
                    'error_age': 'Tafadhali ingiza umri halali wa chanya.',
                    'error_sleep_hours': 'Tafadhali ingiza saa za kulala zinazofaa (0-24).',
                    'error_gender': 'Tafadhali chagua jinsia halali.',
                    'error_activity': 'Tafadhali chagua kiwango cha shughuli halali.'
                }
            };
            let error = '';
            if (!weight || isNaN(weight) || weight <= 0) {
                error = translations[lang]['error_weight'];
            } else if (!height || isNaN(height) || height <= 0) {
                error = translations[lang]['error_height'];
            } else if (!age || isNaN(age) || age <= 0) {
                error = translations[lang]['error_age'];
            } else if (!gender || !['male', 'female'].includes(gender)) {
                error = translations[lang]['error_gender'];
            } else if (!activityLevel || !['low', 'moderate', 'high'].includes(activityLevel)) {
                error = translations[lang]['error_activity'];
            } else if (!sleepHours || isNaN(sleepHours) || sleepHours < 0 || sleepHours > 24) {
                error = translations[lang]['error_sleep_hours'];
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
        function toggleFemaleFields() {
            const gender = document.getElementById('gender').value;
            const femaleFields = document.getElementById('female-fields');
            femaleFields.style.display = gender === 'female' ? 'block' : 'none';
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
                <select id="gender" name="gender" required onchange="toggleFemaleFields()">
                    <option value="" disabled selected>{{ t['select_gender'] }}</option>
                    <option value="male">{{ t['male'] }}</option>
                    <option value="female">{{ t['female'] }}</option>
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
                <label for="chronic_diseases">{{ t['chronic_diseases_label'] }}</label>
                <select id="chronic_diseases" name="chronic_diseases" required>
                    <option value="no">{{ t['no'] }}</option>
                    <option value="yes">{{ t['yes'] }}</option>
                </select>
            </div>
            <div class="form-group">
                <label for="sleep_hours">{{ t['sleep_hours_label'] }}</label>
                <input type="number" id="sleep_hours" name="sleep_hours" step="0.1" required placeholder="e.g., 7.5">
            </div>
            <div class="form-group">
                <label for="sleep_consistency">{{ t['sleep_consistency_label'] }}</label>
                <select id="sleep_consistency" name="sleep_consistency" required>
                    <option value="yes">{{ t['yes'] }}</option>
                    <option value="no">{{ t['no'] }}</option>
                </select>
            </div>
            <div class="form-group">
                <label for="sleep_disturbances">{{ t['sleep_disturbances_label'] }}</label>
                <select id="sleep_disturbances" name="sleep_disturbances" required>
                    <option value="none">{{ t['none'] }}</option>
                    <option value="insomnia">{{ t['insomnia'] }}</option>
                    <option value="waking_tired">{{ t['waking_tired'] }}</option>
                </select>
            </div>
            <div class="form-group">
                <label for="substance_use">{{ t['substance_use_label'] }}</label>
                <select id="substance_use" name="substance_use" required>
                    <option value="yes">{{ t['yes'] }}</option>
                    <option value="no">{{ t['no'] }}</option>
                </select>
            </div>
            <div id="female-fields">
                <div class="form-group">
                    <label for="menstrual_regularity">{{ t['menstrual_regularity_label'] }}</label>
                    <select id="menstrual_regularity" name="menstrual_regularity">
                        <option value="" disabled selected>{{ t['select'] or 'Select' }}</option>
                        <option value="regular">{{ t['regular'] }}</option>
                        <option value="irregular">{{ t['irregular'] }}</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="pregnancy_history">{{ t['pregnancy_history_label'] }}</label>
                    <select id="pregnancy_history" name="pregnancy_history">
                        <option value="" disabled selected>{{ t['select'] or 'Select' }}</option>
                        <option value="has_pregnancy">{{ t['has_pregnancy'] }}</option>
                        <option value="no_pregnancy">{{ t['no_pregnancy'] }}</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="contraceptive_use">{{ t['contraceptive_use_label'] }}</label>
                    <select id="contraceptive_use" name="contraceptive_use">
                        <option value="" disabled selected>{{ t['select'] or 'Select' }}</option>
                        <option value="none">{{ t['contraceptive_none'] }}</option>
                        <option value="pill">{{ t['contraceptive_pill'] }}</option>
                        <option value="iud">{{ t['contraceptive_iud'] }}</option>
                    </select>
                </div>
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
            <p><strong>{{ t['chronic_diseases_label'][:-1] }}</strong> {{ result.chronic_diseases | capitalize }}</p>
            <p><strong>{{ t['sleep_hours_label'][:-1] }}</strong> {{ result.sleep_hours }} hours</p>
            <p><strong>{{ t['sleep_consistency_label'][:-1] }}</strong> {{ result.sleep_consistency | capitalize }}</p>
            <p><strong>{{ t['sleep_disturbances_label'][:-1] }}</strong> {{ result.sleep_disturbances | capitalize }}</p>
            <p><strong>{{ t['substance_use_label'][:-1] }}</strong> {{ result.substance_use | capitalize }}</p>
            {% if result.gender == 'female' and result.menstrual_regularity %}
                <p><strong>{{ t['menstrual_regularity_label'][:-1] }}</strong> {{ result.menstrual_regularity | capitalize }}</p>
            {% endif %}
            {% if result.gender == 'female' and result.pregnancy_history %}
                <p><strong>{{ t['pregnancy_history_label'][:-1] }}</strong> {{ result.pregnancy_history | capitalize }}</p>
            {% endif %}
            {% if result.gender == 'female' and result.contraceptive_use %}
                <p><strong>{{ t['contraceptive_use_label'][:-1] }}</strong> {{ result.contraceptive_use | capitalize }}</p>
            {% endif %}
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
            <th>Chronic Diseases</th>
            <th>Sleep Hours</th>
            <th>Sleep Consistency</th>
            <th>Sleep Disturbances</th>
            <th>Substance Use</th>
            <th>Menstrual Regularity</th>
            <th>Pregnancy History</th>
            <th>Contraceptive Use</th>
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
                <td>{{ record['chronic_diseases'] | capitalize }}</td>
                <td>{{ record['sleep_hours'] }}</td>
                <td>{{ record['sleep_consistency'] | capitalize }}</td>
                <td>{{ record['sleep_disturbances'] | capitalize }}</td>
                <td>{{ record['substance_use'] | capitalize }}</td>
                <td>{{ record['menstrual_regularity'] | capitalize or '' }}</td>
                <td>{{ record['pregnancy_history'] | capitalize or '' }}</td>
                <td>{{ record['contraceptive_use'] | capitalize or '' }}</td>
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
                labels: ['Average BMI', 'Average Water Intake (L)', 'Average Sleep Hours'],
                datasets: [{
                    label: 'Statistics',
                    data: [{{ avg_bmi }}, {{ avg_water }}, {{ avg_sleep }}],
                    backgroundColor: ['#36a2eb', '#4bc0c0', '#ffcd56']
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
