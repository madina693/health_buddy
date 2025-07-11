import os
import io
import csv
import sqlite3
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging and Flask app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'healthbuddy.db')

# Translations for English and Swahili
translations = {
    "en": {
        "title": "HealthBuddy - Your Wellness Companion",
        "intro": "Your personal wellness companion – enter your details for tailored health advice!",
        "about_us_title": "Welcome to HealthBuddy",
        "about_us_content": """
            HealthBuddy is your trusted partner in achieving a healthier lifestyle. 
            We provide personalized health advice based on your unique profile, 
            empowering you to make informed decisions for your well-being. 
            Whether you're managing daily habits or seeking guidance on specific health concerns, 
            we're here to support you every step of the way! 
            <a href='https://www.who.int/health-topics/' class='text-blue-600 underline' target='_blank'>Learn more about health</a> 
            from reliable sources in English and Swahili.
        """,
        "learn_health": "Learn About Health",
        "start_assessment": "Start Health Assessment",
        "agreement_label": "I agree to share my details for health advice",
        "basic_info": "Basic Info",
        "lifestyle": "Lifestyle",
        "nutrition": "Nutrition",
        "female_specific": "Female-Specific Info",
        "weight_label": "Weight (kg):",
        "height_label": "Height (cm):",
        "age_label": "Age:",
        "gender_label": "Gender:",
        "activity_label": "Daily Exercise Level:",
        "chronic_diseases_label": "Chronic Diseases (e.g., diabetes, hypertension, asthma, heart disease):",
        "sleep_hours_label": "Sleep Hours per Night:",
        "sleep_disturbance_label": "Sleep Disturbance at Night:",
        "substance_use_label": "Substance Use (e.g., alcohol, tobacco, marijuana):",
        "mental_health_label": "Mental Health:",
        "fruit_veggie_label": "Vegetable/Fruit Intake (e.g., sukuma wiki, mangoes):",
        "water_consumption_label": "Daily Clean, Safe Water Intake (not juice/soda):",
        "oily_sugary_food_label": "Oily/Sugary Foods (e.g., chips, sweets, sodas):",
        "menstrual_regularity_label": "Menstrual Regularity:",
        "pregnancy_history_label": "Pregnancy History:",
        "contraceptive_use_label": "Contraceptive Use:",
        "submit": "Get Health Advice",
        "select_gender": "Select Gender",
        "select_activity": "Select exercise level",
        "select_mental_health": "Select mental health",
        "select_fruit_veggie": "Select frequency",
        "select_water": "Select amount",
        "select_oily_sugary": "Select frequency",
        "select_sleep_disturbance": "Select sleep disturbance",
        "select_menstrual_regularity": "Select menstrual regularity",
        "select_pregnancy_history": "Select pregnancy history",
        "male": "Male",
        "female": "Female",
        "low": "Low (mostly sitting, <30 min exercise)",
        "moderate": "Moderate (light walking, 30-60 min exercise)",
        "high": "High (active, e.g., sports, >60 min exercise)",
        "yes": "Yes",
        "no": "No",
        "regular": "Regular",
        "irregular": "Irregular",
        "none": "None",
        "insomnia": "Insomnia",
        "waking_tired": "Waking tired",
        "no_disturbance": "No disturbance",
        "good_mental": "Good (happy, calm)",
        "moderate_mental": "Moderate (some stress)",
        "poor_mental": "Poor (frequent stress or sadness)",
        "fruit_veggie_no": "No veggie/fruits",
        "fruit_veggie_daily": "Daily veggie/fruits",
        "fruit_veggie_rarely": "Rarely veggie/fruits",
        "water_glass_1": "1 glass daily",
        "water_glass_2_3": "2-3 glasses daily",
        "water_liter_1": "1 liter daily",
        "water_liter_1_plus": "1+ liters daily",
        "oily_sugary_no": "No Oily/Sugary Foods",
        "oily_sugary_moderate": "Moderate Oily/Sugary Foods",
        "oily_sugary_frequent": "Frequent Oily/Sugary Foods",
        "oily_sugary_daily": "Daily Oily/Sugary Foods",
        "has_pregnancy": "Yes, past pregnancies",
        "no_pregnancy": "No pregnancies",
        "contraceptive_none": "None",
        "contraceptive_pill": "Pill",
        "contraceptive_iud": "IUD",
        "contraceptive_other": "Other",
        "report_title": "Your Health Report",
        "water_intake_title": "Daily Water Intake",
        "health_tips_title": "Your Health Tips",
        "bmi_label": "BMI:",
        "about_us_label": "About Us",
        "about_us_content_short": "HealthBuddy gives simple health advice.",
        "disclaimer_label": "Disclaimer",
        "disclaimer_content": "This app is not a doctor. Consult a healthcare provider.",
        "copyright": "© 2025 HealthToTech",
        "error_weight": "Enter valid weight (e.g., 70).",
        "error_height": "Enter valid height (e.g., 170).",
        "error_age": "Enter valid age (e.g., 30).",
        "error_sleep_hours": "Enter valid sleep hours (0-24, e.g., 7).",
        "error_gender": "Select gender.",
        "error_activity": "Select exercise level.",
        "error_mental_health": "Select mental health status.",
        "error_fruit_veggie": "Select vegetable/fruit intake frequency.",
        "error_water": "Select clean, safe water intake amount.",
        "error_oily_sugary": "Select oily/sugary food frequency.",
        "error_sleep_disturbance": "Select sleep disturbance.",
        "error_agreement": "You must agree to share details to start the assessment.",
        "error_menstrual_regularity": "Select menstrual regularity.",
        "error_pregnancy_history": "Select pregnancy history.",
        "bmi_underweight": "Underweight: Eat more fruits, veggies, ugali, or beans to gain healthy weight.",
        "bmi_healthy": "Healthy weight: Keep eating well and staying active!",
        "bmi_overweight": "Overweight: Walk more, eat less oily/sugary foods to manage weight.",
        "bmi_obese": "High weight: See a doctor, eat more veggies, and reduce oily/sugary foods.",
        "activity_low_youth": "Young? Walk or play sports for 30 min daily to stay active.",
        "activity_low_elderly": "Gentle walking or gardening keeps you strong.",
        "activity_moderate_youth": "Good activity! Try dancing or football to stay fit.",
        "activity_moderate_elderly": "Keep moving with light chores or walking.",
        "activity_high_youth": "Very active! Rest well, drink clean water to maintain energy.",
        "activity_high_elderly": "Great activity! Rest and eat healthy to stay strong.",
        "sleep_poor_youth": "Poor sleep? Aim for 7-9 hours nightly and avoid screens before bed.",
        "sleep_poor_elderly": "Tired from poor sleep? Aim for 7-9 hours and relax before bed.",
        "sleep_good": "Good sleep keeps you strong and happy! Maintain 7-9 hours.",
        "sleep_disturbance_insomnia": "Insomnia? Try a bedtime routine or consult a doctor.",
        "sleep_disturbance_waking_tired": "Waking tired? Ensure 7-9 hours and limit caffeine.",
        "sleep_disturbance_no_disturbance": "No sleep issues? Keep your routine for good health!",
        "mental_poor_youth": "Stressed or sad? Talk to a friend or counselor to feel better.",
        "mental_poor_elderly": "Feeling down? Share with family or a doctor for support.",
        "mental_moderate_youth": "Some stress? Relax with music or a walk to stay calm.",
        "mental_moderate_elderly": "Feeling okay? Rest with family or light activity for peace.",
        "mental_good": "Feeling great! Keep doing what you love to stay happy.",
        "chronic_disease": "For {} (e.g., diabetes, hypertension), see a doctor regularly.",
        "substance_use_yes_youth": "Substance use harms you. Try to stop or seek help from a counselor.",
        "substance_use_yes_elderly": "Substances hurt health. Talk to a doctor for support.",
        "substance_use_no": "Great avoiding substances! Stay healthy.",
        "menstrual_irregular": "Irregular periods? See a doctor for advice.",
        "menstrual_regular": "Regular periods show good health. Keep monitoring.",
        "pregnancy_history": "Past pregnancies? Talk to a doctor for tailored advice.",
        "contraceptive_use": "Using contraceptives? Discuss with a doctor for guidance.",
        "general_nutrition_youth": "Eat ugali, beans, greens to grow strong and healthy.",
        "general_nutrition_elderly": "Choose veggies and fruits to stay healthy and strong."
    },
    "sw": {
        "title": "HealthBuddy - Rafiki Yako wa Afya",
        "intro": "Rafiki yako wa afya – ingiza maelezo yako kwa ushauri wa afya wa kibinafsi!",
        "about_us_title": "Karibu HealthBuddy",
        "about_us_content": """
            HealthBuddy ni mshirika wako wa kuaminika katika kupata maisha yenye afya bora. 
            Tunatoa ushauri wa afya wa kibinafsi kulingana na maelezo yako ya kipekee, 
            tukikupa uwezo wa kufanya maamuzi bora kwa ajili ya afya yako. 
            Iwe unashughulikia tabia za kila siku au unatafuta mwongozo kuhusu masuala ya afya, 
            tuna hapa kukusaidia kila hatua! 
            <a href='https://www.who.int/health-topics/' class='text-blue-600 underline' target='_blank'>Jifunze zaidi kuhusu afya</a> 
            kutoka vyanzo vya kuaminika kwa Kiingereza na Kiswahili.
        """,
        "learn_health": "Jifunze Kuhusu Afya",
        "start_assessment": "Anza Tathmini ya Afya",
        "agreement_label": "Nakubali kushiriki maelezo yangu kwa ushauri wa afya",
        "basic_info": "Taarifa za Msingi",
        "lifestyle": "Mtindo wa Maisha",
        "nutrition": "Lishe",
        "female_specific": "Taarifa za Wanawake",
        "weight_label": "Uzito (kg):",
        "height_label": "Urefu (cm):",
        "age_label": "Umri:",
        "gender_label": "Jinsia:",
        "activity_label": "Kiwango cha Mazoezi ya Kila Siku:",
        "chronic_diseases_label": "Magonjwa ya Muda Mrefu (k.m., kisukari, shinikizo la damu, pumu, ugonjwa wa moyo):",
        "sleep_hours_label": "Saa za Kulala Usiku:",
        "sleep_disturbance_label": "Usumbufu wa Usingizi Usiku:",
        "substance_use_label": "Utumiaji wa Dawa za Kulevya (k.m., pombe, sigara, bangi):",
        "mental_health_label": "Afya ya Akili:",
        "fruit_veggie_label": "Ulaji wa Mboga na Matunda (k.m., sukuma wiki, embe):",
        "water_consumption_label": "UnywajI wa Maji Safi na Salama wa Kila Siku (sio juisi/soda):",
        "oily_sugary_food_label": "Vyakula vya Mafuta/Sukari (k.m., chips, peremende, soda):",
        "menstrual_regularity_label": "Uratibu wa Hedhi:",
        "pregnancy_history_label": "Historia ya Ujauzito:",
        "contraceptive_use_label": "Uzazi wa Mpango:",
        "submit": "Pata Ushauri wa Afya",
        "select_gender": "Chagua Jinsia",
        "select_activity": "Chagua kiwango cha mazoezi",
        "select_mental_health": "Chagua afya ya akili",
        "select_fruit_veggie": "Chagua mara ngapi",
        "select_water": "Chagua kiasi",
        "select_oily_sugary": "Chagua mara ngapi",
        "select_sleep_disturbance": "Chagua usumbufu wa usingizi",
        "select_menstrual_regularity": "Chagua uratibu wa hedhi",
        "select_pregnancy_history": "Chagua historia ya ujauzito",
        "male": "Mwanaume",
        "female": "Mwanamke",
        "low": "Chini (kukaa sana, mazoezi <30 min)",
        "moderate": "Wastani (kutembea kidogo, mazoezi 30-60 min)",
        "high": "Juu (shughuli kama michezo, mazoezi >60 min)",
        "yes": "Ndiyo",
        "no": "Hapana",
        "regular": "Mara kwa mara",
        "irregular": "Sio ya mara kwa mara",
        "none": "Hakuna",
        "insomnia": "Kukosa usingizi",
        "waking_tired": "Kuamka ukiwa umechoka",
        "no_disturbance": "Hakuna usumbufu",
        "good_mental": "Nzuri (furaha, utulivu)",
        "moderate_mental": "Wastani (msongo kidogo)",
        "poor_mental": "Duni (msongo wa mara kwa mara au huzuni)",
        "fruit_veggie_no": "Hakuna mboga/matunda",
        "fruit_veggie_daily": "Mboga/matunda kila siku",
        "fruit_veggie_rarely": "Mboga/matunda mara chache",
        "water_glass_1": "Glasi 1 kila siku",
        "water_glass_2_3": "Glasi 2-3 kila siku",
        "water_liter_1": "Lita 1 kila siku",
        "water_liter_1_plus": "Lita 1+ kila siku",
        "oily_sugary_no": "Hakuna Vyakula vya Mafuta/Sukari",
        "oily_sugary_moderate": "Vyakula vya Mafuta/Sukari Wastani",
        "oily_sugary_frequent": "Vyakula vya Mafuta/Sukari Mara kwa Mara",
        "oily_sugary_daily": "Vyakula vya Mafuta/Sukari Kila Siku",
        "has_pregnancy": "Ndiyo, mimba za awali",
        "no_pregnancy": "Hapana mimba",
        "contraceptive_none": "Hakuna",
        "contraceptive_pill": "Vidonge",
        "contraceptive_iud": "IUD",
        "contraceptive_other": "Nyingine",
        "report_title": "Ripoti Yako ya Afya",
        "water_intake_title": "Ulaji wa Maji",
        "health_tips_title": "Vidokezo vya Afya",
        "bmi_label": "BMI:",
        "about_us_label": "Kuhusu Sisi",
        "about_us_content_short": "HealthBuddy inakupa ushauri rahisi wa afya.",
        "disclaimer_label": "Kanusho",
        "disclaimer_content": "Programu sio daktari. Ongea na daktari.",
        "copyright": "© 2025 HealthToTech",
        "error_weight": "Ingiza uzito halali (k.m., 70).",
        "error_height": "Ingiza urefu halali (k.m., 170).",
        "error_age": "Ingiza umri halali (k.m., 30).",
        "error_sleep_hours": "Ingiza saa za kulala (0-24, k.m., 7).",
        "error_gender": "Chagua jinsia.",
        "error_activity": "Chagua kiwango cha mazoezi.",
        "error_mental_health": "Chagua hali ya afya ya akili.",
        "error_fruit_veggie": "Chagua mara ngapi unakula mboga/matunda.",
        "error_water": "Chagua kiasi cha maji safi na salama.",
        "error_oily_sugary": "Chagua mara ngapi unakula vyakula vya mafuta/sukari.",
        "error_sleep_disturbance": "Chagua usumbufu wa usingizi.",
        "error_agreement": "Lazima ukubali kushiriki maelezo ili kuanza tathmini.",
        "error_menstrual_regularity": "Chagua uratibu wa hedhi.",
        "error_pregnancy_history": "Chagua historia ya ujauzito.",
        "bmi_underweight": "Uzito chini: Kula matunda, mboga, ugali, au maharagwe zaidi ili kupata uzito wa afya.",
        "bmi_healthy": "Uzito sawa: Endelea kula vizuri na kushiriki shughuli!",
        "bmi_overweight": "Uzito zaidi: Tembea zaidi, punguza vyakula vya mafuta/sukari ili kudhibiti uzito.",
        "bmi_obese": "Uzito wa juu: Ongea na daktari, kula mboga zaidi, na punguza vyakula vya mafuta/sukari.",
        "activity_low_youth": "Kijana? Tembea au cheza michezo kwa dakika 30 kila siku ili uwe na shughuli.",
        "activity_low_elderly": "Tembea au lima kwa upole ili uwe na nguvu.",
        "activity_moderate_youth": "Shughuli nzuri! Jaribu kucheza dansi au mpira ili uwe na afya.",
        "activity_moderate_elderly": "Endelea na kazi za nyumbani au kutembea.",
        "activity_high_youth": "Mwenye shughuli! Pumzika vizuri, kunywa maji safi ili kudumisha nguvu.",
        "activity_high_elderly": "Shughuli nzuri! Pumzika na kula vizuri ili uwe na nguvu.",
        "sleep_poor_youth": "Usingizi hafifu? Lenga saa 7-9 usiku na epuka skrini kabla ya kulala.",
        "sleep_poor_elderly": "Usingizi duni? Jaribu saa 7-9 na pumzika kabla ya kulala.",
        "sleep_good": "Usingizi mzuri unakufanya uwe na nguvu! Dumisha saa 7-9.",
        "sleep_disturbance_insomnia": "Kukosa usingizi? Jaribu ratiba ya kulala au ongea na daktari.",
        "sleep_disturbance_waking_tired": "Kuamka ukiwa umechoka? Hakikisha saa 7-9 na punguza kafeini.",
        "sleep_disturbance_no_disturbance": "Hakuna usumbufu wa usingizi? Dumisha ratiba yako kwa afya njema!",
        "mental_poor_youth": "Huzuni au msongo? Ongea na rafiki au mshauri ili ujisikie vizuri.",
        "mental_poor_elderly": "Unahisi chini? Ongea na familia au daktari kwa msaada.",
        "mental_moderate_youth": "Msongo kidogo? Pumzika na muziki au tembea ili uwe na utulivu.",
        "mental_moderate_elderly": "Sawa? Pumzika na familia au shughuli za upole kwa amani.",
        "mental_good": "Unahisi vizuri! Endelea na mambo unayopenda ili uwe na furaha.",
        "chronic_disease": "Kwa {} (k.m., kisukari, shinikizo la damu), tembelea daktari mara kwa mara.",
        "substance_use_yes_youth": "Dawa za kulevya zinadhuru. Jaribu kuacha au tafuta msaada kutoka kwa mshauri.",
        "substance_use_yes_elderly": "Dawa za kulevya zinaumiza afya. Ongea na daktari kwa msaada.",
        "substance_use_no": "Nzuri kuepuka dawa za kulevya! Endelea kuwa na afya.",
        "menstrual_irregular": "Hedhi isiyo ya kawaida? Tembelea daktari kwa ushauri.",
        "menstrual_regular": "Hedhi ya kawaida inaonyesha afya njema. Endelea kufuatilia.",
        "pregnancy_history": "Mimba za zamani? Ongea na daktari kwa ushauri wa kibinafsi.",
        "contraceptive_use": "Unatumia uzazi wa mpango? Jadiliana na daktari kwa mwongozo.",
        "general_nutrition_youth": "Kula ugali, maharagwe, mboga kwa nguvu na afya.",
        "general_nutrition_elderly": "Chagua mboga na matunda kwa afya na nguvu."
    }
}

def init_db():
    """Initialize SQLite database."""
    try:
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS health_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weight REAL, height REAL, age INTEGER, gender TEXT, activity_level TEXT,
                    water_intake REAL, health_tips TEXT, chronic_diseases TEXT, sleep_hours REAL,
                    sleep_disturbance TEXT, substance_use TEXT, mental_health TEXT, 
                    fruit_veggie_intake TEXT, water_consumption TEXT, oily_sugary_food_use TEXT, 
                    menstrual_regularity TEXT, pregnancy_history TEXT, contraceptive_use TEXT, 
                    timestamp TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT
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

def calculate_bmi(weight, height):
    """Calculate BMI."""
    return round(weight / ((height / 100) ** 2), 2)

def calculate_water_intake(weight, activity_level, water_consumption):
    """Calculate recommended water intake."""
    base_ml_per_kg = 30
    multipliers = {'high': 5, 'moderate': 2.5, 'low': 0}
    water_ml = weight * (base_ml_per_kg + multipliers.get(activity_level, 0))
    if water_consumption in ['water_glass_1', 'water_glass_2_3']:
        water_ml += 500
    return round(water_ml / 1000, 2)

def generate_health_tips(age, gender, weight, height, activity_level, chronic_diseases, sleep_hours,
                        sleep_disturbance, substance_use, mental_health, fruit_veggie_intake,
                        water_consumption, oily_sugary_food_use, menstrual_regularity,
                        pregnancy_history, contraceptive_use, lang="en"):
    """Generate personalized health tips, excluding nutrition-related advice."""
    t = translations.get(lang, translations["en"])
    tips = []
    bmi = calculate_bmi(weight, height)
    bmi_categories = {18.5: "bmi_underweight", 25: "bmi_healthy", 30: "bmi_overweight"}
    for threshold, key in bmi_categories.items():
        if bmi < threshold or (key == "bmi_obese" and bmi >= 30):
            tips.append(t[key if key != "bmi_obese" else "bmi_obese"])
            break
    age_group = "youth" if age <= 35 else "elderly"
    tips.append(t[f"activity_{activity_level}_{age_group}"])
    tips.append(t[f"sleep_{'poor' if sleep_hours < 7 else 'good'}_{age_group}"])
    tips.append(t[f"sleep_disturbance_{sleep_disturbance}"])
    mental_health_base = mental_health.replace("_mental", "")
    tips.append(t[f"mental_{mental_health_base}_{age_group}"])
    if chronic_diseases:
        tips.append(t["chronic_disease"].format(chronic_diseases))
    if substance_use.lower() == 'yes':
        tips.append(t[f"substance_use_yes_{age_group}"])
    else:
        tips.append(t["substance_use_no"])
    if gender == 'female':
        if menstrual_regularity:
            tips.append(t[f"menstrual_{menstrual_regularity.lower()}"])
        if pregnancy_history:
            tips.append(t["pregnancy_history"])
        if contraceptive_use != 'none':
            tips.append(t["contraceptive_use"])
    tips.append(t[f"general_nutrition_{age_group}"])
    return tips

@app.route("/", methods=["GET"])
def about():
    """Display About Us page."""
    lang = session.get('lang', request.args.get('lang', 'en'))
    session['lang'] = lang
    t = translations.get(lang, translations["en"])
    return render_template_string(about_template, t=t, lang=lang)

@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    """Handle health assessment."""
    lang = session.get('lang', request.args.get('lang', 'en'))
    session['lang'] = lang
    t = translations.get(lang, translations["en"])
    if request.method == "POST":
        try:
            # Get form data with explicit defaults
            weight = float(request.form.get("weight", 0))
            height = float(request.form.get("height", 0))
            age = int(request.form.get("age", 0))
            gender = request.form.get("gender", "")
            activity_level = request.form.get("activity_level", "")
            chronic_diseases = request.form.get("chronic_diseases", "").strip()
            sleep_hours = float(request.form.get("sleep_hours", 0))
            sleep_disturbance = request.form.get("sleep_disturbance", "")
            substance_use = request.form.get("substance_use", "no").lower()
            mental_health = request.form.get("mental_health", "")
            fruit_veggie_intake = request.form.get("fruit_veggie_intake", "")
            water_consumption = request.form.get("water_consumption", "")
            oily_sugary_food_use = request.form.get("oily_sugary_food_use", "")
            menstrual_regularity = request.form.get("menstrual_regularity", "") if gender == "female" else ""
            pregnancy_history = request.form.get("pregnancy_history", "") if gender == "female" else ""
            contraceptive_use = request.form.get("contraceptive_use", "none") if gender == "female" else "none"

            # Log form data for debugging
            logger.info(f"Form data: weight={weight}, height={height}, age={age}, gender={gender}, "
                        f"activity_level={activity_level}, chronic_diseases={chronic_diseases}, "
                        f"sleep_hours={sleep_hours}, sleep_disturbance={sleep_disturbance}, "
                        f"substance_use={substance_use}, mental_health={mental_health}, "
                        f"fruit_veggie_intake={fruit_veggie_intake}, water_consumption={water_consumption}, "
                        f"oily_sugary_food_use={oily_sugary_food_use}, menstrual_regularity={menstrual_regularity}, "
                        f"pregnancy_history={pregnancy_history}, contraceptive_use={contraceptive_use}")

            # Validate inputs
            errors = {
                "weight": weight <= 0,
                "height": height <= 0,
                "age": age <= 0,
                "gender": gender not in ['male', 'female'],
                "activity_level": activity_level not in ['low', 'moderate', 'high'],
                "sleep_hours": sleep_hours < 0 or sleep_hours > 24,
                "sleep_disturbance": sleep_disturbance not in ['insomnia', 'waking_tired', 'no_disturbance'],
                "mental_health": mental_health not in ['good_mental', 'moderate_mental', 'poor_mental'],
                "fruit_veggie_intake": fruit_veggie_intake not in ['no', 'daily', 'rarely'],
                "water_consumption": water_consumption not in ['water_glass_1', 'water_glass_2_3', 'water_liter_1', 'water_liter_1_plus'],
                "oily_sugary_food_use": oily_sugary_food_use not in ['no', 'moderate', 'frequent', 'daily'],
                "menstrual_regularity": menstrual_regularity not in ['regular', 'irregular'] and gender == 'female',
                "pregnancy_history": pregnancy_history not in ['has_pregnancy', 'no_pregnancy'] and gender == 'female'
            }
            for field, invalid in errors.items():
                if invalid:
                    flash(t[f"error_{field}"], "error")
                    return render_template_string(assessment_template, t=t, lang=lang)

            # Calculate derived values
            water_intake = calculate_water_intake(weight, activity_level, water_consumption)
            health_tips = generate_health_tips(age, gender, weight, height, activity_level, chronic_diseases,
                                             sleep_hours, sleep_disturbance, substance_use, mental_health,
                                             fruit_veggie_intake, water_consumption, oily_sugary_food_use,
                                             menstrual_regularity, pregnancy_history, contraceptive_use, lang)

            # Insert into database
            try:
                with sqlite3.connect(DATABASE) as conn:
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO health_records (
                            weight, height, age, gender, activity_level, water_intake, 
                            health_tips, chronic_diseases, sleep_hours, sleep_disturbance, 
                            substance_use, mental_health, fruit_veggie_intake, 
                            water_consumption, oily_sugary_food_use, menstrual_regularity, 
                            pregnancy_history, contraceptive_use, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        weight, height, age, gender, activity_level, water_intake,
                        ';'.join(health_tips), chronic_diseases, sleep_hours, sleep_disturbance,
                        substance_use, mental_health, fruit_veggie_intake, water_consumption,
                        oily_sugary_food_use, menstrual_regularity, pregnancy_history,
                        contraceptive_use, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    conn.commit()
                    logger.info("Health record saved successfully")
            except sqlite3.Error as e:
                logger.error(f"Failed to save health record: {e}")
                flash(f"Failed to save record: {str(e)}", "error")
                return render_template_string(assessment_template, t=t, lang=lang)

            # Prepare result for display
            result = {
                "weight": weight, "height": height, "age": age, "gender": gender,
                "activity_level": activity_level, "water_intake": water_intake,
                "health_tips": health_tips, "bmi": calculate_bmi(weight, height),
                "chronic_diseases": chronic_diseases, "sleep_hours": sleep_hours,
                "sleep_disturbance": sleep_disturbance, "substance_use": substance_use,
                "mental_health": mental_health, "fruit_veggie_intake": fruit_veggie_intake,
                "water_consumption": water_consumption, "oily_sugary_food_use": oily_sugary_food_use,
                "menstrual_regularity": menstrual_regularity, "pregnancy_history": pregnancy_history,
                "contraceptive_use": contraceptive_use
            }
            return render_template_string(assessment_template, result=result, t=t, lang=lang)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid input: {e}")
            flash("Enter valid numeric values.", "error")
            return render_template_string(assessment_template, t=t, lang=lang)
    return render_template_string(assessment_template, t=t, lang=lang)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Handle admin login."""
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
                    logger.info(f"Admin {username} logged in successfully")
                    return redirect(url_for('admin_dashboard'))
                flash("Invalid credentials.", "error")
        except sqlite3.Error as e:
            logger.error(f"Login error: {e}")
            flash("Login error.", "error")
    return render_template_string(admin_login_template)

@app.route("/admin/dashboard", methods=["GET", "POST"])
def admin_dashboard():
    """Display admin dashboard."""
    if not session.get('admin'):
        flash("Please log in.", "error")
        return redirect(url_for('admin_login'))
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = "SELECT * FROM health_records WHERE 1=1"
            params = []
            for f, v in [("date_filter", ""), ("gender_filter", ['male', 'female']), ("activity_filter", ['low', 'moderate', 'high'])]:
                val = request.form.get(f)
                if val and (not v or val in v):
                    if f == "date_filter":
                        query += " AND date(timestamp) = ?"
                    else:
                        query += f" AND {f.replace('_filter', '')} = ?"
                    params.append(val)
            c.execute(query, params)
            records = [dict(row) for row in c.fetchall()]
            c.execute("SELECT AVG(weight / ((height / 100) * (height / 100))) as avg_bmi, AVG(water_intake) as avg_water, AVG(sleep_hours) as avg_sleep FROM health_records")
            stats = c.fetchone()
            stats = {k: round(v, 2) if v else 0 for k, v in stats.items()}
            c.execute("SELECT COUNT(DISTINCT id) as total_users FROM health_records")
            user_count = c.fetchone()['total_users']
        return render_template_string(admin_dashboard_template, records=records, stats=stats, user_count=user_count)
    except sqlite3.Error as e:
        logger.error(f"Dashboard error: {e}")
        flash("Dashboard error.", "error")
        return redirect(url_for('admin_login'))

@app.route("/admin/logout")
def admin_logout():
    """Handle admin logout."""
    session.pop('admin', None)
    flash("Logged out.", "success")
    return redirect(url_for('admin_login'))

@app.route("/admin/export_csv")
def export_csv():
    """Export health records to CSV."""
    if not session.get('admin'):
        flash("Please log in.", "error")
        return redirect(url_for('admin_login'))
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM health_records")
            records = c.fetchall()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Weight (kg)', 'Height (cm)', 'Age', 'Gender', 'Activity Level',
                         'Water Intake (L)', 'BMI', 'Chronic Diseases', 'Sleep Hours', 'Sleep Disturbance',
                         'Substance Use', 'Mental Health', 'Fruit/Veggie Intake', 'Water Consumption',
                         'Oily/Sugary Food Use', 'Menstrual Regularity', 'Pregnancy History',
                         'Contraceptive Use', 'Health Tips', 'Timestamp'])
        for r in records:
            bmi = calculate_bmi(r['weight'], r['height'])
            writer.writerow([r['id'], r['weight'], r['height'], r['age'], r['gender'], r['activity_level'],
                            r['water_intake'], round(bmi, 2), r['chronic_diseases'], r['sleep_hours'],
                            r['sleep_disturbance'], r['substance_use'], r['mental_health'],
                            r['fruit_veggie_intake'], r['water_consumption'], r['oily_sugary_food_use'],
                            r['menstrual_regularity'], r['pregnancy_history'], r['contraceptive_use'],
                            r['health_tips'], r['timestamp']])
        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv',
                        as_attachment=True, download_name='healthbuddy_records.csv')
    except sqlite3.Error as e:
        logger.error(f"Export error: {e}")
        flash("Export error.", "error")
        return redirect(url_for('admin_dashboard'))

# Templates
about_template = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t['title'] }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function toggleAssessmentButton() {
            const checkbox = document.getElementById('agreement');
            const button = document.getElementById('start-assessment');
            button.disabled = !checkbox.checked;
            button.classList.toggle('opacity-50', !checkbox.checked);
            button.classList.toggle('cursor-not-allowed', !checkbox.checked);
        }
        function changeLanguage(lang) {
            window.location.href = '?lang=' + lang;
        }
    </script>
</head>
<body class="min-h-screen bg-gradient-to-br from-cyan-50 to-green-100 flex flex-col">
    <header class="bg-green-800 text-white p-4 sticky top-0 z-10">
        <div class="container mx-auto flex flex-col sm:flex-row justify-between items-center">
            <h1 class="text-xl sm:text-2xl font-bold mb-2 sm:mb-0">HealthToTech</h1>
            <select onchange="changeLanguage(this.value)" class="bg-green-700 p-2 rounded text-sm sm:text-base">
                <option value="en" {% if lang == 'en' %}selected{% endif %}>English</option>
                <option value="sw" {% if lang == 'sw' %}selected{% endif %}>Swahili</option>
            </select>
        </div>
    </header>
    <main class="container mx-auto p-4 flex-grow">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ 'bg-red-100 text-red-800' if category == 'error' else 'bg-green-100 text-green-800' }} p-4 rounded mb-4 text-center text-sm sm:text-base">{{ message }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="bg-white p-6 sm:p-8 rounded-lg shadow-md text-center">
            <h2 class="text-2xl sm:text-3xl font-bold text-green-800 mb-4">{{ t['about_us_title'] }}</h2>
            <p class="text-gray-700 mb-6 text-sm sm:text-base">{{ t['about_us_content'] | safe }}</p>
            <label class="flex justify-center items-center space-x-2 mb-6">
                <input type="checkbox" id="agreement" name="agreement" onchange="toggleAssessmentButton()" class="h-4 w-4 text-green-600">
                <span class="text-green-700 text-sm sm:text-base">{{ t['agreement_label'] }}</span>
            </label>
            <div class="flex flex-col sm:flex-row justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                <a id="start-assessment" href="{{ url_for('assessment', lang=lang) }}" class="bg-green-600 text-white py-2 px-4 rounded opacity-50 cursor-not-allowed text-sm sm:text-base" disabled>{{ t['start_assessment'] }}</a>
            </div>
        </div>
    </main>
    <footer class="bg-green-800 text-white p-4 text-center">
        <p class="text-sm sm:text-base">{{ t['about_us_content_short'] }} | {{ t['disclaimer_content'] }} | {{ t['copyright'] }}</p>
    </footer>
</body>
</html>
"""

assessment_template = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t['title'] }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        function validateForm() {
            const fields = {
                weight: { value: document.getElementById('weight').value, error: 'error_weight', cond: v => !v || isNaN(v) || v <= 0 },
                height: { value: document.getElementById('height').value, error: 'error_height', cond: v => !v || isNaN(v) || v <= 0 },
                age: { value: document.getElementById('age').value, error: 'error_age', cond: v => !v || isNaN(v) || v <= 0 },
                gender: { value: document.getElementById('gender').value, error: 'error_gender', cond: v => !['male', 'female'].includes(v) },
                activity_level: { value: document.getElementById('activity_level').value, error: 'error_activity', cond: v => !['low', 'moderate', 'high'].includes(v) },
                sleep_hours: { value: document.getElementById('sleep_hours').value, error: 'error_sleep_hours', cond: v => !v || isNaN(v) || v < 0 || v > 24 },
                sleep_disturbance: { value: document.getElementById('sleep_disturbance').value, error: 'error_sleep_disturbance', cond: v => !['insomnia', 'waking_tired', 'no_disturbance'].includes(v) },
                mental_health: { value: document.getElementById('mental_health').value, error: 'error_mental_health', cond: v => !['good_mental', 'moderate_mental', 'poor_mental'].includes(v) },
                fruit_veggie_intake: { value: document.getElementById('fruit_veggie_intake').value, error: 'error_fruit_veggie', cond: v => !['no', 'daily', 'rarely'].includes(v) },
                water_consumption: { value: document.getElementById('water_consumption').value, error: 'error_water', cond: v => !['water_glass_1', 'water_glass_2_3', 'water_liter_1', 'water_liter_1_plus'].includes(v) },
                oily_sugary_food_use: { value: document.getElementById('oily_sugary_food_use').value, error: 'error_oily_sugary', cond: v => !['no', 'moderate', 'frequent', 'daily'].includes(v) },
                menstrual_regularity: { value: document.getElementById('menstrual_regularity').value, error: 'error_menstrual_regularity', cond: v => document.getElementById('gender').value === 'female' && !['regular', 'irregular'].includes(v) },
                pregnancy_history: { value: document.getElementById('pregnancy_history').value, error: 'error_pregnancy_history', cond: v => document.getElementById('gender').value === 'female' && !['has_pregnancy', 'no_pregnancy'].includes(v) }
            };
            for (let [key, { value, error, cond }] of Object.entries(fields)) {
                if (cond(value)) {
                    document.getElementById('error').innerText = translations['{{ lang }}'][error];
                    document.getElementById('error').style.display = 'block';
                    return false;
                }
            }
            return true;
        }
        function toggleFemaleFields() {
            document.getElementById('female-fields').classList.toggle('hidden', document.getElementById('gender').value !== 'female');
        }
        function changeLanguage(lang) {
            window.location.href = '?lang=' + lang;
        }
        const translations = {{ t | tojson | safe }};
    </script>
</head>
<body class="min-h-screen bg-gradient-to-br from-cyan-50 to-green-100 flex flex-col">
    <header class="bg-green-800 text-white p-4 sticky top-0 z-10">
        <div class="container mx-auto flex flex-col sm:flex-row justify-between items-center">
            <h1 class="text-xl sm:text-2xl font-bold mb-2 sm:mb-0">HealthToTech</h1>
            <select onchange="changeLanguage(this.value)" class="bg-green-700 p-2 rounded text-sm sm:text-base">
                <option value="en" {% if lang == 'en' %}selected{% endif %}>English</option>
                <option value="sw" {% if lang == 'sw' %}selected{% endif %}>Swahili</option>
            </select>
        </div>
    </header>
    <main class="container mx-auto p-4 flex-grow">
        <p class="text-center text-gray-700 mb-6 text-sm sm:text-base">{{ t['intro'] }}</p>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ 'bg-red-100 text-red-800' if category == 'error' else 'bg-green-100 text-green-800' }} p-4 rounded mb-4 text-center text-sm sm:text-base">{{ message }}</p>
                {% endfor %}
            {% else %}
                <p id="error" class="hidden bg-red-100 text-red-800 p-4 rounded mb-4 text-center text-sm sm:text-base"></p>
            {% endif %}
        {% endwith %}
        <form method="POST" onsubmit="return validateForm()" class="space-y-6">
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['basic_info'] }}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['weight_label'] }}</label><input type="number" id="weight" name="weight" step="0.1" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="e.g., 70.5"></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['height_label'] }}</label><input type="number" id="height" name="height" step="0.1" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="e.g., 170"></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['age_label'] }}</label><input type="number" id="age" name="age" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="e.g., 30"></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['gender_label'] }}</label><select id="gender" name="gender" required onchange="toggleFemaleFields()" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_gender'] }}</option><option value="male">{{ t['male'] }}</option><option value="female">{{ t['female'] }}</option></select></div>
                </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['lifestyle'] }}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['activity_label'] }}</label><select id="activity_level" name="activity_level" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_activity'] }}</option><option value="low">{{ t['low'] }}</option><option value="moderate">{{ t['moderate'] }}</option><option value="high">{{ t['high'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['chronic_diseases_label'] }}</label><textarea id="chronic_diseases" name="chronic_diseases" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="{{ t['chronic_diseases_label'][:-1] }}"></textarea></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['sleep_hours_label'] }}</label><input type="number" id="sleep_hours" name="sleep_hours" step="0.1" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="e.g., 7.5"></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['sleep_disturbance_label'] }}</label><select id="sleep_disturbance" name="sleep_disturbance" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_sleep_disturbance'] }}</option><option value="insomnia">{{ t['insomnia'] }}</option><option value="waking_tired">{{ t['waking_tired'] }}</option><option value="no_disturbance">{{ t['no_disturbance'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['substance_use_label'] }}</label><textarea id="substance_use" name="substance_use" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base" placeholder="{{ t['substance_use_label'][:-1] }}"></textarea></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['mental_health_label'] }}</label><select id="mental_health" name="mental_health" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_mental_health'] }}</option><option value="good_mental">{{ t['good_mental'] }}</option><option value="moderate_mental">{{ t['moderate_mental'] }}</option><option value="poor_mental">{{ t['poor_mental'] }}</option></select></div>
                </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['nutrition'] }}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['fruit_veggie_label'] }}</label><select id="fruit_veggie_intake" name="fruit_veggie_intake" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_fruit_veggie'] }}</option><option value="no">{{ t['fruit_veggie_no'] }}</option><option value="daily">{{ t['fruit_veggie_daily'] }}</option><option value="rarely">{{ t['fruit_veggie_rarely'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['water_consumption_label'] }}</label><select id="water_consumption" name="water_consumption" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_water'] }}</option><option value="water_glass_1">{{ t['water_glass_1'] }}</option><option value="water_glass_2_3">{{ t['water_glass_2_3'] }}</option><option value="water_liter_1">{{ t['water_liter_1'] }}</option><option value="water_liter_1_plus">{{ t['water_liter_1_plus'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['oily_sugary_food_label'] }}</label><select id="oily_sugary_food_use" name="oily_sugary_food_use" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_oily_sugary'] }}</option><option value="no">{{ t['oily_sugary_no'] }}</option><option value="moderate">{{ t['oily_sugary_moderate'] }}</option><option value="frequent">{{ t['oily_sugary_frequent'] }}</option><option value="daily">{{ t['oily_sugary_daily'] }}</option></select></div>
                </div>
            </div>
            <div id="female-fields" class="bg-white p-6 rounded-lg shadow-md hidden">
                <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['female_specific'] }}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['menstrual_regularity_label'] }}</label><select id="menstrual_regularity" name="menstrual_regularity" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_menstrual_regularity'] }}</option><option value="regular">{{ t['regular'] }}</option><option value="irregular">{{ t['irregular'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['pregnancy_history_label'] }}</label><select id="pregnancy_history" name="pregnancy_history" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="" disabled selected>{{ t['select_pregnancy_history'] }}</option><option value="has_pregnancy">{{ t['has_pregnancy'] }}</option><option value="no_pregnancy">{{ t['no_pregnancy'] }}</option></select></div>
                    <div><label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">{{ t['contraceptive_use_label'] }}</label><select id="contraceptive_use" name="contraceptive_use" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base"><option value="none">{{ t['contraceptive_none'] }}</option><option value="pill">{{ t['contraceptive_pill'] }}</option><option value="iud">{{ t['contraceptive_iud'] }}</option><option value="other">{{ t['contraceptive_other'] }}</option></select></div>
                </div>
            </div>
            <div class="bg-white p-6 rounded-lg shadow-md">
                <button type="submit" class="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 text-sm sm:text-base">{{ t['submit'] }}</button>
            </div>
        </form>
        {% if result %}
            <div class="mt-8 space-y-6">
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h3 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['report_title'] }}</h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm sm:text-base">
                        <p><strong>{{ t['weight_label'][:-1] }}</strong> {{ result.weight }} kg</p>
                        <p><strong>{{ t['height_label'][:-1] }}</strong> {{ result.height }} cm</p>
                        <p><strong>{{ t['age_label'][:-1] }}</strong> {{ result.age }}</p>
                        <p><strong>{{ t['gender_label'][:-1] }}</strong> {{ result.gender | capitalize }}</p>
                        <p><strong>{{ t['activity_label'][:-1] }}</strong> {{ t[result.activity_level] }}</p>
                        <p><strong>{{ t['bmi_label'] }}</strong> {{ result.bmi }}</p>
                        {% if result.chronic_diseases %}<p><strong>{{ t['chronic_diseases_label'][:-1] }}</strong> {{ result.chronic_diseases }}</p>{% endif %}
                        <p><strong>{{ t['sleep_hours_label'][:-1] }}</strong> {{ result.sleep_hours }} hours</p>
                        <p><strong>{{ t['sleep_disturbance_label'][:-1] }}</strong> {{ t[result.sleep_disturbance] }}</p>
                        <p><strong>{{ t['substance_use_label'][:-1] }}</strong> {{ result.substance_use }}</p>
                        <p><strong>{{ t['mental_health_label'][:-1] }}</strong> {{ t[result.mental_health] }}</p>
                        <p><strong>{{ t['fruit_veggie_label'][:-1] }}</strong> {{ t[result.fruit_veggie_intake] }}</p>
                        <p><strong>{{ t['water_consumption_label'][:-1] }}</strong> {{ t[result.water_consumption] }}</p>
                        <p><strong>{{ t['oily_sugary_food_label'][:-1] }}</strong> {{ t[result.oily_sugary_food_use] }}</p>
                        {% if result.gender == 'female' and result.menstrual_regularity %}<p><strong>{{ t['menstrual_regularity_label'][:-1] }}</strong> {{ result.menstrual_regularity | capitalize }}</p>{% endif %}
                        {% if result.gender == 'female' and result.pregnancy_history %}<p><strong>{{ t['pregnancy_history_label'][:-1] }}</strong> {{ result.pregnancy_history | capitalize }}</p>{% endif %}
                        {% if result.gender == 'female' and result.contraceptive_use != 'none' %}<p><strong>{{ t['contraceptive_use_label'][:-1] }}</strong> {{ result.contraceptive_use | capitalize }}</p>{% endif %}
                    </div>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h3 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['water_intake_title'] }}</h3>
                    <p>{{ result.water_intake }} liters</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h3 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">{{ t['health_tips_title'] }}</h3>
                    <ul class="list-disc pl-5 text-sm sm:text-base">
                        {% for tip in result.health_tips %}
                            <li>{{ tip }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        {% endif %}
    </main>
    <footer class="bg-green-800 text-white p-4 text-center">
        <p class="text-sm sm:text-base">{{ t['about_us_content_short'] }} | {{ t['disclaimer_content'] }} | {{ t['copyright'] }}</p>
    </footer>
</body>
</html>
"""

admin_login_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HealthBuddy Admin Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gradient-to-br from-cyan-50 to-green-100 flex items-center justify-center">
    <div class="bg-white p-6 sm:p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 class="text-xl sm:text-2xl font-bold text-green-800 mb-6 text-center">Admin Login</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ 'bg-red-100 text-red-800' if category == 'error' else 'bg-green-100 text-green-800' }} p-4 rounded mb-4 text-center text-sm sm:text-base">{{ message }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST">
            <div class="mb-4">
                <label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">Username</label>
                <input type="text" name="username" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base">
            </div>
            <div class="mb-4">
                <label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">Password</label>
                <input type="password" name="password" required class="w-full p-2 border border-green-300 rounded text-sm sm:text-base">
            </div>
            <button type="submit" class="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 text-sm sm:text-base">Login</button>
        </form>
    </div>
</body>
</html>
"""

admin_dashboard_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HealthBuddy Admin Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gradient-to-br from-cyan-50 to-green-100">
    <header class="bg-green-800 text-white p-4 sticky top-0 z-10">
        <div class="container mx-auto flex flex-col sm:flex-row justify-between items-center">
            <h1 class="text-xl sm:text-2xl font-bold mb-2 sm:mb-0">HealthBuddy Admin Dashboard</h1>
            <a href="{{ url_for('admin_logout') }}" class="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 text-sm sm:text-base">Logout</a>
        </div>
    </header>
    <main class="container mx-auto p-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <p class="{{ 'bg-red-100 text-red-800' if category == 'error' else 'bg-green-100 text-green-800' }} p-4 rounded mb-4 text-center text-sm sm:text-base">{{ message }}</p>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">Statistics</h2>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm sm:text-base">
                <p><strong>Total Users:</strong> {{ user_count }}</p>
                <p><strong>Average BMI:</strong> {{ stats.avg_bmi }}</p>
                <p><strong>Average Water Intake:</strong> {{ stats.avg_water }} liters</p>
                <p><strong>Average Sleep Hours:</strong> {{ stats.avg_sleep }} hours</p>
            </div>
        </div>
        <div class="bg-white p-6 rounded-lg shadow-md mb-6">
            <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">Filter Records</h2>
            <form method="POST" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                    <label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">Date</label>
                    <input type="date" name="date_filter" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base">
                </div>
                <div>
                    <label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">Gender</label>
                    <select name="gender_filter" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base">
                        <option value="">All</option>
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                    </select>
                </div>
                <div>
                    <label class="block text-green-700 font-medium mb-1 text-sm sm:text-base">Activity Level</label>
                    <select name="activity_filter" class="w-full p-2 border border-green-300 rounded text-sm sm:text-base">
                        <option value="">All</option>
                        <option value="low">Low</option>
                        <option value="moderate">Moderate</option>
                        <option value="high">High</option>
                    </select>
                </div>
                <div class="sm:col-span-3">
                    <button type="submit" class="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 text-sm sm:text-base">Filter</button>
                </div>
            </form>
        </div>
        <div class="bg-white p-6 rounded-lg shadow-md">
            <h2 class="text-lg sm:text-xl font-semibold text-green-800 mb-4">Health Records</h2>
            <a href="{{ url_for('export_csv') }}" class="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 mb-4 inline-block text-sm sm:text-base">Export to CSV</a>
            <div class="overflow-x-auto">
                <table class="w-full border-collapse">
                    <thead>
                        <tr class="bg-green-600 text-white">
                            <th class="p-2 border text-sm sm:text-base">ID</th>
                            <th class="p-2 border text-sm sm:text-base">Weight</th>
                            <th class="p-2 border text-sm sm:text-base">Height</th>
                            <th class="p-2 border text-sm sm:text-base">Age</th>
                            <th class="p-2 border text-sm sm:text-base">Gender</th>
                            <th class="p-2 border text-sm sm:text-base">Activity</th>
                            <th class="p-2 border text-sm sm:text-base">Water (L)</th>
                            <th class="p-2 border text-sm sm:text-base">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for record in records %}
                            <tr class="hover:bg-green-50">
                                <td class="p-2 border text-sm sm:text-base">{{ record.id }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.weight }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.height }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.age }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.gender | capitalize }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.activity_level | capitalize }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.water_intake }}</td>
                                <td class="p-2 border text-sm sm:text-base">{{ record.timestamp }}</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </main>
</body>
</html>
"""

if __name__ == "__main__":
    try:
        init_db()
        app.run(debug=True)
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        raise
