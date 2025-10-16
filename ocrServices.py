import smtplib
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime,timedelta, timezone
from PIL import Image
import pytesseract
import io
import requests
from dotenv import load_dotenv
import os
import re
load_dotenv()

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
WEB_APP_URL = os.getenv("WEB_APP_URL_LINK")

def scan_card(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("L")  
        text = pytesseract.image_to_string(image, lang='eng')
        print("OCR Text:\n", text)
        return text
    except Exception as e:
        print("Local OCR failed:", e)
        return None

def extract_contact_info(ocr_text):
    try:
        contact = {}
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, ocr_text)
        contact['email'] = emails[0] if emails else None
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\d{10})'
        phones = re.findall(phone_pattern, ocr_text.replace(" ", "").replace("-", ""))
        contact['phone'] = "+91" + phones[0][1] if phones else None
        lines = [line.strip() for line in ocr_text.split("\n") if line.strip()]
        lines = [line for line in lines if not re.search(email_pattern, line) 
                 and not re.search(phone_pattern, line.replace(" ", ""))]
        contact['name'] = lines[0] if len(lines) >= 1 else None
        company = None
        if len(lines) > 1:
            for line in lines[1:]:
                if any(k in line.lower() for k in ["inc", "llc", "ltd", "company", "corp", "co."]):
                    company = line
                    break
            if not company:
                company = lines[1]
        contact['company'] = company

        return contact
    except Exception as e:
        print("Failed to extract contact info:", e)
        return {"name": None, "email": None, "phone": None, "company": None}

def determine_priority(contact):
    high_keywords = ["CEO", "Managing Director", "Founder", "VP", "Manager", "Director"]
    for keyword in high_keywords:
        if keyword.lower() in contact.get("company", "").lower() or \
           keyword.lower() in contact.get("name", "").lower():
            return "High"
    return "Normal"

def send_to_google_sheet(contact=None):
    try:
        if contact is None:
            contact = {
                "name": "John Doe",
                "company": "Example Corp",
                "Email": "john@example.com",
                "phone": "+911234567890",
                "Priority": "lower",
                "Email-sent": "No",
                "Approved": "N/A"
            }
            print("Using dummy data for testing.")

        contact["priority"] = determine_priority(contact)

        if contact["priority"] == "High":
            contact["approved"] = "Pending"
        else:
            contact["approved"] = "Approved"

        contact["emailSent"] = "No"
        print(f"Priority: {contact['priority']}, Approved: {contact['approved']}, Email Sent: {contact['emailSent']}")
        response = requests.post(WEB_APP_URL, json=contact)
        if response.status_code == 200:
            print("Contact saved to Google Sheet!")
            print("Response:", response.text)
        else:
            print(f"Failed to save: Status {response.status_code}, Response: {response.text}")
    except Exception as e:
        print("Exception while sending to Google Sheet:", e)


def send_email_to_user(contact_data,
                       from_email="gd.geetanjalidubey@gmail.com",
                       app_password=os.getenv("Email_APP_PASSWORD")):
    try:
        print("Attempting to send email to contact:", contact_data) 
        to_email = contact_data.get("email") or contact_data.get("Email")
        if not to_email:
            print("No email found in contact data")
            return

        contact_data["email"] = to_email 
        contact_data["name"] = contact_data.get("name") or contact_data.get("Name", "there")
        contact_data["company"] = contact_data.get("company") or contact_data.get("Company", "")
        contact_data["priority"] = contact_data.get("priority") or contact_data.get("Priority", "Normal")
        contact_data["approved"] = contact_data.get("approved") or contact_data.get("Approved", "Pending")

        subject = f"Hello {contact_data.get('name')}, Please Approve Your Contact Info"
        message_body = f"""
Hello {contact_data.get('name')}!
Your contact info has been added to our system:
- Name: {contact_data.get('name')}
- Company: {contact_data.get('company')}
- Email: {contact_data.get('Email')}
- Phone: {contact_data.get('phone')}
- Priority: {contact_data.get('priority')}
- Approved: {contact_data.get('approved')}
Please review and approve if you are a high-priority contact.
Thank you!
"""
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"Personalized email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def get_pending_contacts():
    try:
        response = requests.get(WEB_APP_URL)
        print("HTTP status:", response.status_code)
        print("Response text:", response.text)
        if response.status_code == 200:
            data = response.json()
            print(f"Pending contacts fetched: {len(data)}")
            return data
        return []
    except Exception as e:
        print(f"Failed to fetch pending contacts: {e}")
        return []


def process_pending_emails():
    print("Checking pending contacts...", datetime.now())
    pending_contacts = get_pending_contacts()
    print("Pending contacts:", pending_contacts)

    for contact in pending_contacts:
        date_met_str = contact.get("Date Met")
        if not date_met_str:
            continue

        try:
            date_met = datetime.fromisoformat(date_met_str.replace("Z", "+00:00"))
        except Exception as e:
            print(f"Failed to parse Date Met for contact {contact.get('Name')}: {e}")
            continue

        now_utc = datetime.now(timezone.utc)
        if now_utc - date_met >= timedelta(hours=24):
            send_email_to_user(contact)
            mark_email_sent(contact)
        else:
            print(f"Email not sent yet for {contact.get('Name')} (less than 24 hours)")

def mark_email_sent(contact):
    try:
        contact["emailSent"] = "Yes"
        requests.put(WEB_APP_URL, json=contact)  # <-- This is a PUT request ✅
    except Exception as e:
        print(f"Failed to mark email as sent: {e}")

def start_email_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_pending_emails, 'interval', minutes=1)
    scheduler.start()
    print("Email scheduler started. Will check pending contacts every 1 minute.")
