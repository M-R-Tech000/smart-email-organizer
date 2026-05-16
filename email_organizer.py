import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
from transformers import pipeline
import pandas as pd

load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def connect_to_email():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail
    except Exception as e:
        print(f"Error: {e}")
        return None

def classify_email(subject, body):
    text_to_check = (subject + " " + body).lower()
    if any(word in text_to_check for word in ["invoice", "payment", "receipt", "billing", "فاتورة", "دفع"]):
        return "Financial"
    elif any(word in text_to_check for word in ["meeting", "schedule", "zoom", "calendar", "call", "اجتماع"]):
        return "Calendar & Meetings"
    elif any(word in text_to_check for word in ["support", "help", "client", "customer", "question", "عميل"]):
        return "Customer Support"
    else:
        return "General"

def summarize_text(text):
    if len(text.split()) < 20:
        return text
    try:
        summary = summarizer(text[:1024], max_length=45, min_length=10, do_sample=False)
        return summary[0]['summary_text']
    except Exception:
        return "Summary failed"

def process_emails(mail):
    mail.select("inbox")
    status, messages = mail.search(None, 'UNSEEN')
    mail_ids = messages[0].split()
    
    email_data_list = []
    
    for i in mail_ids[-3:]:
        status, msg_data = mail.fetch(i, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes): 
                    subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                
                from_sender, encoding = decode_header(msg["From"])[0]
                if isinstance(from_sender, bytes): 
                    from_sender = from_sender.decode(encoding if encoding else "utf-8", errors="ignore")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                
                body = body.strip()
                category = classify_email(subject, body)
                summary = summarize_text(body) if body else "No text content"
                
                email_data_list.append({
                    "From": from_sender,
                    "Subject": subject,
                    "Category": category,
                    "AI Summary": summary
                })

    if email_data_list:
        df = pd.DataFrame(email_data_list)
        print(df.to_string(index=False))
        df.to_csv("daily_email_digest.csv", index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    mail_connection = connect_to_email()
    if mail_connection:
        process_emails(mail_connection)
        mail_connection.logout()



