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

# Configure Streamlit page
st.set_page_config(
    page_title="🤺 Fencing Lesson Manager",
    page_icon="🤺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'canceled_lessons' not in st.session_state:
    st.session_state.canceled_lessons = []
if 'contacts_db' not in st.session_state:
    st.session_state.contacts_db = pd.read_csv('contacts.csv').to_json(orient='records')#[]
if 'notification_log' not in st.session_state:
    st.session_state.notification_log = []

# Configuration - In production, use st.secrets
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


def get_week_dates(start_date=None):
    """Get week dates starting from Sunday"""
    if start_date:
        if isinstance(start_date, str):
            base_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            base_date = start_date
    else:
        base_date = datetime.now()

    # Find the most recent Sunday
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


def log_notification(message):
    """Add message to notification log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.notification_log.append(f"[{timestamp}] {message}")


def notify_available_slot(lesson_info):
    """Notify all contacts about available slot"""
    subject = f"🤺 Fencing Lesson Available - {lesson_info['date']} at {lesson_info['time']}"
    email_body = f"""
A fencing lesson slot has become available!

📅 Date: {lesson_info['date']}
⏰ Time: {lesson_info['time']} (25 minutes)
👤 Originally scheduled for: {lesson_info['original_student']}

This slot is available on a first-come, first-served basis.
Please respond quickly if you're interested!

Best regards,
Your Fencing Coach
    """

    sms_body = f"🤺 Fencing lesson available {lesson_info['date']} at {lesson_info['time']}. First come, first served. Reply if interested!"

    results = []
    for contact in st.session_state.contacts_db:
        contact_name = contact.get('name', 'Unknown')

        # Send email if available
        if contact.get('email'):
            email_success, email_msg = send_email(contact['email'], subject, email_body)
            result_msg = f"Email to {contact_name}: {email_msg}"
            results.append(result_msg)
            log_notification(result_msg)

        # Send SMS if available
        if contact.get('phone'):
            sms_success, sms_msg = send_sms(contact['phone'], sms_body)
            result_msg = f"SMS to {contact_name}: {sms_msg}"
            results.append(result_msg)
            log_notification(result_msg)

    return results


def notify_lesson_filled(lesson_info, selected_contact, remaining_contacts):
    """Notify about lesson being filled"""
    # Notify selected contact (confirmation)
    confirm_subject = f"✅ Fencing Lesson Confirmed - {lesson_info['date']} at {lesson_info['time']}"
    confirm_email = f"""
Congratulations! Your fencing lesson has been confirmed:

📅 Date: {lesson_info['date']}
⏰ Time: {lesson_info['time']} (25 minutes)

Please arrive 5 minutes early. See you there!

Best regards,
Your Fencing Coach
    """

    confirm_sms = f"✅ Fencing lesson confirmed for {lesson_info['date']} at {lesson_info['time']}. Arrive 5 min early!"

    # Notify remaining contacts (slot filled)
    filled_subject = f"❌ Fencing Lesson Filled - {lesson_info['date']} at {lesson_info['time']}"
    filled_email = f"""
The fencing lesson slot for {lesson_info['date']} at {lesson_info['time']} has been filled by another student.

Thank you for your interest! We'll notify you of future available slots.

Best regards,
Your Fencing Coach
    """

    filled_sms = f"❌ Fencing lesson {lesson_info['date']} at {lesson_info['time']} has been filled. Thanks for your interest!"

    results = []

    # Send confirmation to selected contact
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

    # Send filled notification to remaining contacts
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


def main():
    # Header
    st.title("🤺 Fencing Lesson Manager")
    st.markdown("### Manage canceled lessons and fill slots automatically")

    # Sidebar for configuration
    with st.sidebar:
        st.header("📋 Configuration")

        # Upload contacts CSV
        st.subheader("Upload Contacts")
        uploaded_file = st.file_uploader("Choose CSV file", type="csv")

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state.contacts_db = df.to_dict('records')
                st.success(f"✅ Loaded {len(st.session_state.contacts_db)} contacts")

                # Show sample of contacts
                st.subheader("Contacts Preview")
                st.dataframe(df.head(), use_container_width=True)

            except Exception as e:
                st.error(f"Error loading CSV: {str(e)}")

        # Configuration status
        st.subheader("System Status")
        email_configured = bool(EMAIL_CONFIG['email'] and EMAIL_CONFIG['password'])
        sms_configured = bool(TWILIO_CONFIG['account_sid'] and TWILIO_CONFIG['auth_token'])

        st.write(f"📧 Email: {'✅ Configured' if email_configured else '❌ Not configured'}")
        st.write(f"📱 SMS: {'✅ Configured' if sms_configured else '❌ Not configured'}")
        st.write(f"👥 Contacts: {len(st.session_state.contacts_db)} loaded")

    # Main content area
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.metric("Available Lessons",
                  len([l for l in st.session_state.canceled_lessons if l['status'] == 'available']))

    with col2:
        st.metric("Filled Lessons", len([l for l in st.session_state.canceled_lessons if l['status'] == 'filled']))

    with col3:
        st.metric("Total Contacts", len(st.session_state.contacts_db))

    # Week selection
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

        # Display week as buttons
        st.write("**Week Days:**")
        day_cols = st.columns(7)

        selected_date = None
        for i, day in enumerate(week_dates):
            with day_cols[i]:
                if st.button(f"{day['day']}\n{day['display'].split(', ')[1]}", key=f"day_{i}"):
                    selected_date = day['date']
                    st.session_state.selected_date = selected_date

    # Add cancellation section
    st.header("❌ Add Canceled Lesson")

    with st.form("add_cancellation_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            lesson_date = st.selectbox(
                "Select Date",
                options=[day['date'] for day in week_dates],
                format_func=lambda x: next(day['display'] for day in week_dates if day['date'] == x)
            )

        with col2:
            lesson_time = st.selectbox("Select Time", generate_time_slots())

        with col3:
            original_student = st.text_input("Original Student Name")

        submitted = st.form_submit_button("➕ Add Cancellation & Notify Contacts")

        if submitted:
            if lesson_date and lesson_time and original_student:
                # Create cancellation record
                cancellation = {
                    'id': len(st.session_state.canceled_lessons) + 1,
                    'date': lesson_date,
                    'time': lesson_time,
                    'original_student': original_student,
                    'status': 'available',
                    'created_at': datetime.now().isoformat()
                }

                st.session_state.canceled_lessons.append(cancellation)

                # Automatically notify all contacts
                if st.session_state.contacts_db:
                    with st.spinner("Sending notifications..."):
                        results = notify_available_slot(cancellation)

                    st.success(f"✅ Cancellation added and {len(results)} notifications sent!")

                    # Show notification results
                    with st.expander("View notification results"):
                        for result in results:
                            st.write(f"• {result}")
                else:
                    st.warning("⚠️ Cancellation added but no contacts loaded for notifications")
            else:
                st.error("Please fill in all fields")

    # Display available lessons
    st.header("📋 Available Lessons")

    available_lessons = [l for l in st.session_state.canceled_lessons if l['status'] == 'available']

    if available_lessons:
        for lesson in available_lessons:
            with st.expander(f"🕐 {lesson['date']} at {lesson['time']} (was {lesson['original_student']})"):
                st.write(f"**Original Student:** {lesson['original_student']}")
                st.write(f"**Created:** {lesson['created_at']}")

                if st.session_state.contacts_db:
                    # Contact selection for filling the slot
                    contact_names = [contact.get('name', 'Unknown') for contact in st.session_state.contacts_db]

                    selected_contact_name = st.selectbox(
                        "Select contact to fill this slot:",
                        options=contact_names,
                        key=f"contact_{lesson['id']}"
                    )

                    if st.button(f"✅ Fill Slot with {selected_contact_name}", key=f"fill_{lesson['id']}"):
                        # Find the selected contact
                        selected_contact = next(
                            (c for c in st.session_state.contacts_db if c.get('name') == selected_contact_name),
                            None
                        )

                        if selected_contact:
                            # Update lesson status
                            lesson['status'] = 'filled'
                            lesson['filled_by'] = selected_contact_name
                            lesson['filled_at'] = datetime.now().isoformat()

                            # Get remaining contacts
                            remaining_contacts = [
                                c for c in st.session_state.contacts_db
                                if c.get('name') != selected_contact_name
                            ]

                            # Send notifications
                            with st.spinner("Sending confirmation and filled notifications..."):
                                results = notify_lesson_filled(lesson, selected_contact, remaining_contacts)

                            st.success(f"✅ Lesson filled by {selected_contact_name}!")
                            st.rerun()
                else:
                    st.info("📤 Upload contacts CSV to enable slot filling")
    else:
        st.info("No available lessons at the moment")

    # Display filled lessons
    filled_lessons = [l for l in st.session_state.canceled_lessons if l['status'] == 'filled']

    if filled_lessons:
        st.header("✅ Filled Lessons")

        for lesson in filled_lessons:
            with st.expander(f"✅ {lesson['date']} at {lesson['time']} - Filled by {lesson['filled_by']}"):
                st.write(f"**Original Student:** {lesson['original_student']}")
                st.write(f"**Filled By:** {lesson['filled_by']}")
                st.write(f"**Filled At:** {lesson['filled_at']}")

    # Notification log
    if st.session_state.notification_log:
        st.header("📧 Notification Log")

        with st.expander("View notification history"):
            for log_entry in reversed(st.session_state.notification_log[-20:]):  # Show last 20 entries
                st.code(log_entry, language=None)

    # Auto-refresh option
    st.sidebar.header("🔄 Auto-refresh")
    auto_refresh = st.sidebar.checkbox("Enable auto-refresh (30 seconds)")

    if auto_refresh:
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()