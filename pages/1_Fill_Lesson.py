import streamlit as st
import pandas as pd
from datetime import datetime
import os

# To share functions across pages, you can import from the parent directory
# This assumes your project structure is set up correctly.
# In a real app, you might put these in a separate 'utils.py' file.
try:
    from revisions import save_lessons_to_csv, get_week_dates, send_email, send_sms, log_notification, notify_lesson_filled, EMAIL_CONFIG, TWILIO_CONFIG, load_lessons_from_csv
except ImportError:
    st.error("Could not load functions from revisions.py. Please check your project structure.")
    st.stop()

# --- Main Page Logic ---
def fill_lesson_page():
    st.set_page_config(
        page_title="Fill Lesson",
        page_icon="✅"
    )

    # --- NEW: Initialize session state variables needed for this page ---
    if 'notification_log' not in st.session_state:
        st.session_state.notification_log = []
    # --- END NEW ---

    st.title("✅ Fencing Lesson Availability")

    # Get lesson_id and contact_id from the URL parameters
    params = st.query_params
    lesson_id = params.get('lesson_id')
    contact_id = params.get('contact_id')

    # Load data
    lessons = st.session_state.get('canceled_lessons', load_lessons_from_csv())
    contacts = st.session_state.get('contacts_db')
    
    if not contacts:
        # Load contacts if not already in session state
        try:
            contacts_df = pd.read_csv("contacts.csv")
            contacts = contacts_df.to_dict('records')
        except Exception as e:
            st.warning("Contacts data not loaded. Functionality will be limited.")

    # --- Check if a specific lesson was requested via URL ---
    if lesson_id and contact_id:
        st.subheader("Confirm Your Lesson Slot")
        
        selected_contact = next((c for c in contacts if str(c.get('contact_id')) == contact_id), None)
        lesson_to_fill = next((l for l in lessons if str(l['id']) == lesson_id and l['status'] == 'available'), None)

        if not lesson_to_fill or not selected_contact:
            st.error("This lesson is no longer available or the link is invalid.")
            return

        # Display lesson details for confirmation
        st.info(f"You are about to claim this lesson slot:")
        st.markdown(f"""
        * **Coach:** {lesson_to_fill['coach']}
        * **Date:** {lesson_to_fill['date']}
        * **Time:** {lesson_to_fill['time']}
        * **With:** {selected_contact['name']}
        """)

        if st.button("✅ Confirm and Fill This Lesson"):
            with st.spinner("Confirming lesson and sending notifications..."):
                # Update the lesson's status in the session state
                lesson_to_fill['status'] = 'filled'
                lesson_to_fill['filled_by'] = selected_contact['name']
                lesson_to_fill['filled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')

                # Save the entire updated list to the CSV
                csv_success, csv_msg = save_lessons_to_csv(lessons)
                
                # Send notifications
                remaining_contacts = [c for c in contacts if str(c.get('contact_id')) != contact_id]
                notify_lesson_filled(lesson_to_fill, selected_contact, remaining_contacts)

                if csv_success:
                    st.success("🎉 Success! Your lesson has been confirmed.")
                    log_notification("Lesson filled via external link.")
                else:
                    st.error("There was an error updating the lesson log.")
                
                st.button("Close") # Give the user a clear action to close the window
    
    else:
        # --- If no specific lesson is in the URL, show all available lessons ---
        st.subheader("Available Lessons Calendar")
        available_lessons = [l for l in lessons if l['status'] == 'available']
        if available_lessons:
            # Sort by date and time
            sorted_lessons = sorted(available_lessons, key=lambda x: (x['date'], x['time']))
            for lesson in sorted_lessons:
                st.markdown(f"**{lesson['date']} at {lesson['time']}** with Coach {lesson['coach']}")
                st.write(f"_Originally scheduled for {lesson['original_student']}_")
                st.write("To claim this slot, a unique link must be used from your email or text notification.")
                st.markdown("---")
        else:
            st.info("There are no available lessons at the moment.")
    
if __name__ == '__main__':
    fill_lesson_page()