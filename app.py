from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import ocrServices

app = Flask(__name__)
CORS(app)

@app.route("/upload-card", methods=["POST"])
def upload_card():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    print("File received:", file.filename)    
    try:
        image_bytes = file.read()
        ocr_text = ocrServices.scan_card(image_bytes)
        if not ocr_text:
            return jsonify({"error": "OCR failed"}), 500

        contact_data = ocrServices.extract_contact_info(ocr_text)
        print("Extracted data:", contact_data)
        threading.Thread(target=async_send_to_sheet, args=(contact_data,)).start()
        return jsonify({
            "status": "success",
            "contact": contact_data
        })
    except Exception as e:
        print("Error in upload_card:", e)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

def async_send_to_sheet(contact):
    try:
        from datetime import datetime, timedelta
        ocrServices.send_to_google_sheet(contact)
        print("Data sent to Google Sheet (async).")
        
    except Exception as e:
        print("Failed to send to Google Sheet (async):", e)

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=ocrServices.start_email_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print("Scheduler running in thread... Press Ctrl+C to exit.")
    app.run(debug=True, use_reloader=False)

