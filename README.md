# 🤺 Fencing Lesson Manager - Deployment Guide


## URL
https://lessnmanager.streamlit.app/


This Streamlit app helps fencing coaches manage canceled lessons and automatically notify contacts via email and SMS.

## Features

✅ **Week-based scheduling** - Choose any week starting from Sunday
✅ **CSV contact upload** - Upload your contact list with names, emails, and phone numbers
✅ **Automatic notifications** - Notify all contacts when a lesson is canceled
✅ **First-come-first-served** - Members click a custom URL to claim lesson
✅ **Dual notifications** - Confirmation to selected contact, "filled" notification to others
✅ **Real-time updates** - See notification status and history

## Testing
1. Click browse to load contacts.csv
2. There should already be a few sample lessons in canceled_lesson_log.csv  
3. You can add a new canceled lesson and see a list of available lessons and the csv log
4. To simulate filling a lesson you go to /Fill_Lesson?lesson_id=1&contact_id=3, for example
5. You would adjust these parameters to reflect and available lesson_id & contact_id

## CSV Format

Your contacts CSV should have these columns:
```csv
contact_id,name,email,phone
1,John Smith,john@email.com,+1234567890
2,Jane Doe,jane@email.com,+1987654321
```

## Usage Workflow

1. **Upload Contacts**: Use the sidebar to upload your CSV file
2. **Select Week**: Choose the week you want to manage
3. **Add Cancellation**: 
   - Select date, time, coach and original student
   - Click "Add Cancellation & Notify Contacts"
   - All contacts receive email and SMS notifications
4. **Fill Slots**:
   - Member clicks a custom URL to fill a specific lesson
   - Confirms they want the lesson at URL 
   - Selected contact gets confirmation
   - Other contacts get "filled" notification
   - Lesson filled displayed or no longer available displayed

## Notification Examples

### Available Slot Notification
**Email Subject**: 🤺 Fencing Lesson Available - 2024-01-15 at 15:30
**SMS**: 🤺 Fencing lesson available 2024-01-15 at 15:30. First come, first served. [Click here to take this lesson](https::/some.com)!

### Confirmation (Selected Contact)
**Email Subject**: ✅ Fencing Lesson Confirmed - 2024-01-15 at 15:30
**SMS**: ✅ Fencing lesson confirmed for 2024-01-15 at 15:30. Arrive 5 min early!

### Filled Notification (Other Contacts)
**Email Subject**: ❌ Fencing Lesson Filled - 2024-01-15 at 15:30  
**SMS**: ❌ Fencing lesson 2024-01-15 at 15:30 has been filled. Thanks for your interest!


## Deployment Options

### Option 1: Streamlit Cloud (Done for testing)

1. **Create GitHub Repository**
   - Initialize git locally 
   - add all files and commit - requirements.txt must be included or probably .toml file works  
   - create github repo
   - push to GitHub

2. **Deploy to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub account
   - Select your repository
   - Click "Deploy"

3. **Configure Secrets**
   - In Streamlit Cloud, go to your app settings
   - Add secrets in the "Secrets" section:
   ```toml
   # Email Configuration
   smtp_server = "smtp.gmail.com"
   smtp_port = 587
   email_address = "your-email@gmail.com"
   email_password = "your-app-password"
   
   # Twilio Configuration
   twilio_account_sid = "your-twilio-sid"
   twilio_auth_token = "your-twilio-token"
   twilio_phone = "+1234567890"
   ```

### Option 2: Heroku

1. **Create Heroku App**
   ```bash
   heroku create your-fencing-app
   git push heroku main
   ```

2. **Set Environment Variables**
   ```bash
   heroku config:set EMAIL_ADDRESS=your-email@gmail.com
   heroku config:set EMAIL_PASSWORD=your-app-password
   heroku config:set TWILIO_ACCOUNT_SID=your-twilio-sid
   heroku config:set TWILIO_AUTH_TOKEN=your-twilio-token
   heroku config:set TWILIO_PHONE=+1234567890
   ```

### Option 3: Local Development

1. **Install Requirements**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create Local Secrets**
   Create `.streamlit/secrets.toml` with your credentials

3. **Run the App**
   ```bash
   streamlit run app.py
   ```

## Email Setup (Gmail)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Create App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Use App Password** (not your regular password) in the configuration

## Twilio Setup

1. **Create Twilio Account** at [twilio.com](https://twilio.com)
2. **Get Phone Number** from Twilio Console
3. **Find Credentials**:
   - Account SID and Auth Token from Console Dashboard
   - Phone number from Phone Numbers section


## Troubleshooting

### Email Not Sending
- Check if 2FA is enabled on Gmail
- Verify you're using App Password, not regular password
- Check spam folder for test emails

### SMS Not Sending  
- Verify Twilio credentials are correct
- Check phone number format (+1234567890)
- Ensure Twilio account has sufficient balance

### CSV Upload Issues
- Ensure CSV has 'name', 'email', 'phone' columns
- Check for empty rows or special characters
- Save CSV in UTF-8 encoding

## Cost Considerations

- **Streamlit Cloud**: Free tier available
- **Email**: Free with Gmail
- **SMS**: Twilio charges per message (~$0.0075 per SMS)
- **Heroku**: Free tier discontinued, paid plans start at $5/month

## Security Notes

- Never commit secrets to GitHub
- Use environment variables or Streamlit secrets
- Regularly rotate API keys and passwords
- Consider using OAuth for email instead of app passwords

## Support

For issues or questions:
1. Check the notification log in the app
2. Verify all credentials are correctly configured
3. Test with a single contact first
4. Check email/SMS provider documentation