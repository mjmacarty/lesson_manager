import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import os
from datetime import datetime, timedelta
import json
import time

# --- Configuration ---
# Your secrets are now loaded from the secrets.toml file
EMAIL_CONFIG = {
    'smtp_server': st.secrets.get('smtp_server', 'smtp.gmail.com'),
    'smtp_port': st.secrets.get('smtp_port', 587),
    'email': st.secrets.get('email_address', ''),
    'password': st.secrets.get('email_password', '')
}

TWILIO_CONFIG = {
    'account_sid': st.secrets.get('twilio_account_sid', ''),
    'auth_token': st.secrets.get('twilio_auth_token', ''),
    'phone_number': st.secrets.get('twilio_phone', '')
}

BASE_URL = st.secrets.get('app_url', 'https://your-streamlit-app-url.streamlit.app') 

# --- New Data Persistence Functions (using st.secrets) ---
def load_lessons_from_secrets():
    """Load lessons from the secrets.toml file."""
    try:
        lessons_json = st.secrets.get('lesson_data', '[]')
        lessons = json.loads(lessons_json)
        return lessons
    except Exception as e:
        st.error(f"Error loading lessons from secrets: {str(e)}")
        return []

def save_lessons_to_secrets(lessons_list):
    """Save lessons to the secrets.toml file."""
    try:
        lessons_json = json.dumps(lessons_list)
        st.secrets['lesson_data'] = lessons_json
        return True, "Lessons saved to secrets"
    except Exception as e:
        return False, f"Error saving lessons to secrets: {str(e)}"

# --- Helper functions ---
def get_week_dates(start_date=None):
    """Get week dates starting from Sunday"""
    if start_date:
        if isinstance(start_date, str):
            base_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            base_date = start_date
    else:
        base_date = datetime.now()
    days_since_sunday = base_date.weekday() + 1
    if days_since_sunday == 7:
        days_since_sunday = 0
    sunday = base_date - timedelta(days=days_since_sunday)
    week_dates = []
    for i in range(7):
        date = sunday + timedelta(days=i)
        week_dates.append({
            'date': date.strftime('%Y-%m-%d'),
            'day': date.strftime('%a'),
            'display': date.strftime('%a, %b %d'),
            'datetime': date
        })
    return week_dates

def generate_time_slots():
    """Generate 30-minute time slots from 9:00 AM to 8:00 PM"""
    slots = []
    start_time = datetime.strptime("09:00", "%H:%M")
    end_time = datetime.strptime("20:00", "%H:%M")
    current_time = start_time
    while current_time <= end_time:
        slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=30)
    return slots

def send_email(to_email, subject, body):
    """Send email notification"""
    if not EMAIL_CONFIG['email'] or not EMAIL_CONFIG['password']:
        return False, "Email configuration not set"
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, f"Email error: {str(e)}"

def send_sms(to_phone, message):
    """Send SMS notification"""
    if not TWILIO_CONFIG['account_sid'] or not TWILIO_CONFIG['auth_token']:
        return False, "SMS configuration not set"
    try:
        client = Client(TWILIO_CONFIG['account_sid'], TWILIO_CONFIG['auth_token'])
        message = client.messages.create(
            body=message,
            from_=TWILIO_CONFIG['phone_number'],
            to=to_phone
        )
        return True, "SMS sent successfully"
    except Exception as e:
        return False, f"SMS error: {str(e)}"

def get_csv_stats():
    """Calculate and return CSV log statistics based on new headers."""
    stats = {
        'total_cancellations': 0,
        'total_filled': 0,
        'fill_rate': 0.0,
        'recent_activity': 0
    }
    lessons = load_lessons_from_secrets() # Load data from secrets
    if lessons:
        try:
            df = pd.DataFrame(lessons)
            stats['total_cancellations'] = len(df)
            stats['total_filled'] = len(df[df['status'] == 'filled'])
            if stats['total_cancellations'] > 0:
                stats['fill_rate'] = round((stats['total_filled'] / stats['total_cancellations']) * 100, 2)
            seven_days_ago = datetime.now() - timedelta(days=7)
            
            # Use 'date entered' column from the DataFrame for date calculation
            df['date entered'] = pd.to_datetime(df['date entered'])
            stats['recent_activity'] = len(df[df['date entered'] >= seven_days_ago])
        except Exception as e:
            st.error(f"Error calculating CSV stats: {str(e)}")
    return stats

def log_notification(message):
    """Log notifications to session state."""
    st.session_state.notification_log.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def notify_available_slot(lesson_info):
    """Notify all contacts about available slot with a unique link"""
    subject = f"🤺 Fencing Lesson Available with {lesson_info['coach']} - {lesson_info['date']} at {lesson_info['time']}"
    
    results = []
    contacts_list = st.session_state.contacts_db
    for contact in contacts_list:
        contact_name = contact.get('name', 'Unknown')
        
        # Create a unique link that points to the new page
        fill_link = f"{BASE_URL}/Fill_Lesson?lesson_id={lesson_info['id']}&contact_id={contact.get('contact_id')}"
        
        email_body = f"""
A fencing lesson slot has become available!

📅 **Date:** {lesson_info['date']}
⏰ **Time:** {lesson_info['time']} (25 minutes)
👨‍🏫 **Coach:** {lesson_info['coach']}
👤 **Originally Scheduled For:** {lesson_info['original_student']}

To claim this lesson, simply click the link below:
{fill_link}

This slot is available on a first-come, first-served basis.

Best regards,
Your Fencing Coach
        """
        sms_body = f"🤺 Fencing lesson with {lesson_info['coach']} is available on {lesson_info['date']} at {lesson_info['time']}. Claim it now: {fill_link}"
        
        if contact.get('email'):
            email_success, email_msg = send_email(contact['email'], subject, email_body)
            result_msg = f"Email to {contact_name}: {email_msg}"
            results.append(result_msg)
            log_notification(result_msg)
        if contact.get('phone'):
            sms_success, sms_msg = send_sms(contact['phone'], sms_body)
            result_msg = f"SMS to {contact_name}: {sms_msg}"
            results.append(result_msg)
            log_notification(result_msg)
    return results

def notify_lesson_filled(lesson_info, selected_contact, remaining_contacts):
    """Notify about lesson being filled"""
    confirm_subject = f"✅ Fencing Lesson Confirmed with {lesson_info['coach']} - {lesson_info['date']} at {lesson_info['time']}"
    confirm_email = f"""
Congratulations! Your fencing lesson has been confirmed:
📅 **Date:** {lesson_info['date']}
⏰ **Time:** {lesson_info['time']} (25 minutes)
👨‍🏫 **Coach:** {lesson_info['coach']}
Please arrive 5 minutes early. See you there!
Best regards,
Your Fencing Coach
    """
    confirm_sms = f"✅ Fencing lesson confirmed with {lesson_info['coach']} for {lesson_info['date']} at {lesson_info['time']}. Arrive 5 min early!"
    filled_subject = f"❌ Fencing Lesson Filled with {lesson_info['coach']} - {lesson_info['date']} at {lesson_info['time']}"
    filled_email = f"""
The fencing lesson slot with {lesson_info['coach']} for {lesson_info['date']} at {lesson_info['time']} has been filled by another student.
Thank you for your interest! We'll notify you of future available slots.
Best regards,
Your Fencing Coach
    """
    filled_sms = f"❌ Fencing lesson with {lesson_info['coach']} on {lesson_info['date']} at {lesson_info['time']} has been filled. Thanks for your interest!"
    results = []
    if selected_contact.get('email'):
        success, msg = send_email(selected_contact['email'], confirm_subject, confirm_email)
        result_msg = f"✅ Confirmation email to {selected_contact['name']}: {msg}"
        results.append(result_msg)
        log_notification(result_msg)
    if selected_contact.get('phone'):
        success, msg = send_sms(selected_contact['phone'], confirm_sms)
        result_msg = f"✅ Confirmation SMS to {selected_contact['name']}: {msg}"
        results.append(result_msg)
        log_notification(result_msg)
    for contact in remaining_contacts:
        if contact.get('email'):
            success, msg = send_email(contact['email'], filled_subject, filled_email)
            result_msg = f"❌ Filled notification email to {contact['name']}: {msg}"
            results.append(result_msg)
            log_notification(result_msg)
        if contact.get('phone'):
            success, msg = send_sms(contact['phone'], filled_sms)
            result_msg = f"❌ Filled notification SMS to {contact['name']}: {msg}"
            results.append(result_msg)
            log_notification(result_msg)
    return results

# --- Main App Function ---
def main():
    st.set_page_config(
        page_title="🤺 Fencing Lesson Manager",
        page_icon="🤺",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    if 'canceled_lessons' not in st.session_state:
        st.session_state.canceled_lessons = load_lessons_from_secrets()
    if 'contacts_db' not in st.session_state:
        st.session_state.contacts_db = []
    if 'notification_log' not in st.session_state:
        st.session_state.notification_log = []

    st.title("🤺 Fencing Lesson Manager")
    st.markdown("### Manage canceled lessons and fill slots automatically")

    with st.sidebar:
        st.header("📋 Configuration")
        st.subheader("Upload Contacts")
        uploaded_file = st.file_uploader("Choose CSV file", type="csv")
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state.contacts_db = df.to_dict('records')
                st.success(f"✅ Loaded {len(st.session_state.contacts_db)} contacts")
                st.subheader("Contacts Preview")
                st.dataframe(df.head(), use_container_width=True)
            except Exception as e:
                st.error(f"Error loading CSV: {str(e)}")
        st.subheader("System Status")
        email_configured = bool(EMAIL_CONFIG['email'] and EMAIL_CONFIG['password'])
        sms_configured = bool(TWILIO_CONFIG['account_sid'] and TWILIO_CONFIG['auth_token'])
        st.write(f"📧 Email: {'✅ Configured' if email_configured else '❌ Not configured'}")
        st.write(f"📱 SMS: {'✅ Configured' if sms_configured else '❌ Not configured'}")
        st.write(f"👥 Contacts: {len(st.session_state.contacts_db)} loaded")
        st.subheader("📊 Lessons Log Statistics")
        csv_stats = get_csv_stats()
        st.write(f"📝 Total Cancellations: {csv_stats['total_cancellations']}")
        st.write(f"✅ Total Filled: {csv_stats['total_filled']}")
        st.write(f"📈 Fill Rate: {csv_stats['fill_rate']}%")
        st.write(f"🕐 Recent Activity (7 days): {csv_stats['recent_activity']}")

        # --- NEW: Download button for secrets data ---
        if csv_stats['total_cancellations'] > 0:
            lessons = load_lessons_from_secrets()
            df = pd.DataFrame(lessons)
            csv_data = df.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Lessons Log",
                data=csv_data,
                file_name="fencing_lessons_log.csv",
                mime="text/csv"
            )

        st.subheader("🛠️ Developer Tools")
        if st.button("Reload Lessons from Secrets"):
            st.session_state.canceled_lessons = []
            st.session_state.canceled_lessons = load_lessons_from_secrets()
            st.success("Lessons reloaded from secrets!")
            st.rerun()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.metric("Available Lessons", len([l for l in st.session_state.canceled_lessons if l['status'] == 'available']))
    with col2:
        st.metric("Filled Lessons", len([l for l in st.session_state.canceled_lessons if l['status'] == 'filled']))
    with col3:
        st.metric("Total Contacts", len(st.session_state.contacts_db))

    st.header("📅 Select Week")
    col1, col2 = st.columns([1, 2])
    with col1:
        selected_start_date = st.date_input(
            "Choose week starting date",
            value=datetime.now(),
            help="Select any date - the app will show the week starting from Sunday"
        )
    with col2:
        week_dates = get_week_dates(selected_start_date)
        st.write("**Week Days:**")
        day_cols = st.columns(7)
        selected_date = None
        for i, day in enumerate(week_dates):
            with day_cols[i]:
                if st.button(f"{day['day']}\n{day['display'].split(', ')[1]}", key=f"day_{i}"):
                    selected_date = day['date']
                    st.session_state.selected_date = selected_date

    st.header("❌ Add Canceled Lesson")
    with st.form("add_cancellation_form"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            lesson_date = st.selectbox(
                "Select Date",
                options=[day['date'] for day in week_dates],
                format_func=lambda x: next(day['display'] for day in week_dates if day['date'] == x)
            )
        with col2:
            lesson_time = st.selectbox("Select Time", generate_time_slots())
        with col3:
            coach_name = st.selectbox("Select Coach", ["Julian", "Frederick"])
        with col4:
            original_student = st.text_input("Original Student Name")
        submitted = st.form_submit_button("➕ Add Cancellation & Notify Contacts")
        if submitted:
            if lesson_date and lesson_time and coach_name and original_student:
                cancellation = {
                    'id': len(st.session_state.canceled_lessons) + 1,
                    'date': lesson_date,
                    'time': lesson_time,
                    'coach': coach_name,
                    'original_student': original_student,
                    'status': 'available',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                st.session_state.canceled_lessons.append(cancellation)
                csv_success, csv_msg = save_lessons_to_secrets(st.session_state.canceled_lessons)
                if csv_success:
                    log_notification(f"Cancellation logged to secrets: {csv_msg}")
                else:
                    st.warning(f"Logging failed: {csv_msg}")
                if st.session_state.contacts_db:
                    with st.spinner("Sending notifications..."):
                        results = notify_available_slot(cancellation)
                    st.success(f"✅ Cancellation added and {len(results)} notifications sent!")
                    with st.expander("View notification results"):
                        for result in results:
                            st.write(f"• {result}")
                        if csv_success:
                            st.write(f"• Secrets: {csv_msg}")
                else:
                    st.warning("⚠️ Cancellation added but no contacts loaded for notifications")
                st.rerun()
            else:
                st.error("Please fill in all fields")

    st.header("📋 Available Lessons")
    available_lessons = [l for l in st.session_state.canceled_lessons if l['status'] == 'available']
    if available_lessons:
        for lesson in available_lessons:
            with st.expander(f"🕐 {lesson['date']} at {lesson['time']} with {lesson['coach']} (was {lesson['original_student']})"):
                st.write(f"**Coach:** {lesson['coach']}")
                st.write(f"**Original Student:** {lesson['original_student']}")
                st.write(f"**Created:** {lesson['created_at']}")
                st.info("To fill this slot, a contact must use the link from the notification message.")
    else:
        st.info("No available lessons at the moment")

    filled_lessons = [l for l in st.session_state.canceled_lessons if l['status'] == 'filled']
    if filled_lessons:
        st.header("✅ Filled Lessons")
        for lesson in filled_lessons:
            with st.expander(f"✅ {lesson['date']} at {lesson['time']} with {lesson['coach']} - Filled by {lesson['filled_by']}"):
                st.write(f"**Coach:** {lesson['coach']}")
                st.write(f"**Original Student:** {lesson['original_student']}")
                st.write(f"**Filled By:** {lesson['filled_by']}")
                st.write(f"**Filled At:** {lesson['filled_at']}")

    if st.session_state.notification_log:
        st.header("📧 Notification Log")
        with st.expander("View notification history"):
            for log_entry in reversed(st.session_state.notification_log[-20:]):
                st.code(log_entry, language=None)

    st.sidebar.header("🔄 Auto-refresh")
    auto_refresh = st.sidebar.checkbox("Enable auto-refresh (30 seconds)")
    if auto_refresh:
        time.sleep(30)
        st.rerun()

if __name__ == "__main__":
    main()