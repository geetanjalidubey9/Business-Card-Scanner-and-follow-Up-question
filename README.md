Step 1: User Uploads the Business Card

    The user uploads a business card image through the frontend.
    
    The Flask backend receives this file at the /upload-card route.
    
    The image file is read in bytes and passed to the OCR service (scan_card):

Step 2: OCR (Optical Character Recognition) Extraction

    The image bytes are passed to the scan_card() function in ocrServices.py.
    
    Using Tesseract OCR, the image is converted to text.
    
    The text is printed and returned for further processing.


Step 3: Extracting Contact Information

    The raw OCR text is passed to the extract_contact_info() function.
    
    Using Regex patterns, it automatically extracts:
    
    Name
    
    Email
    
    Phone number
    
    Company name
    
    like:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+911234567890",
        "company": "TechCorp"
    }

Step 4: Sending Data to Google Sheets (Async)

    Once data is extracted, a new background thread (async_send_to_sheet) sends the contact information to a Google Sheet via an Apps Script API (the WEB_APP_URL from .env).

Step 5: Determining Contact Priority

    Inside send_to_google_sheet(), the system decides if the contact is High Priority or Normal, based on keywords like CEO, Founder, Director, VP, Manager.
    
    High-priority contacts are marked as “Pending” for approval, while normal contacts are auto-approved.

Step 6: Email Scheduler Starts (Background Task)

    When the Flask app starts, a background thread launches a scheduler using APScheduler.
    
    This scheduler automatically checks every 1 minute for contacts who:
    
    Have been added for more than 24 hours
    
    Have not yet been emailed

Step 7: Processing Pending Emails

The function process_pending_emails() fetches all contacts from Google Sheets.

    It checks the “Date Met” field for each contact.
    
    If more than 24 hours have passed, it sends a personalized follow-up email.
    
    Uses Python’s smtplib library to send emails via Gmail SMTP.
    
    Sending Personalized Follow-Up Email
    
    The function send_email_to_user() builds a custom email message with details such as:
    
    Name
    
    Company
    
    Priority
    
    Approval status

Step 9: Updating Google Sheet (Email Sent)
    
    Once an email is sent successfully, the sheet is updated via a PUT request.
    
    The “Email Sent” column is marked as “Yes”.
