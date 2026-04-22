import os
import time
import base64
import json
import pickle
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Get from console.groq.com (free!)

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

YOUR_NAME     = "Sara"                # Your name
YOUR_BUSINESS = "Business"         # Your business name
BOT_TONE      = "professional"        # professional / friendly / apologetic

# MODE: "draft" = saves to Gmail Drafts (you review before sending)
#       "auto"  = sends reply immediately
#       "both"  = sends AND saves draft copy
MODE = "auto"

CHECK_INTERVAL = 30

# ════════════════════════════════════════════════
SCOPES       = ["https://www.googleapis.com/auth/gmail.modify"]
REPLIED_FILE = "replied_ids.json"

groq_client = Groq(api_key=GROQ_API_KEY)

def get_gmail_service():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("gmail", "v1", credentials=creds)

def load_replied_ids():
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_replied_id(email_id):
    ids = load_replied_ids()
    ids.add(email_id)
    with open(REPLIED_FILE, "w") as f:
        json.dump(list(ids), f)

def get_email_body(payload):
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data", "")
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                break
            elif "parts" in part:
                body = get_email_body(part)
                if body:
                    break
    elif payload.get("mimeType") == "text/plain":
        data = payload["body"].get("data", "")
        body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return body.strip()

def should_skip(sender, subject):
    skip_patterns = [
        "no-reply", "noreply", "do-not-reply", "donotreply",
        "newsletter", "unsubscribe", "mailer-daemon",
        "notifications@", "updates@", "alerts@",
        "support@google", "accounts@google",
    ]
    combined = (sender + subject).lower()
    return any(p in combined for p in skip_patterns)

def generate_reply(sender_name, subject, body):
    print(f"  🤖 Generating reply for: {subject[:50]}...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""You are a {BOT_TONE} email assistant for {YOUR_BUSINESS}.
Write an email reply to this message from {sender_name}.

Subject: {subject}
Message:
{body[:1500]}

Instructions:
- Be {BOT_TONE} and genuine
- Keep it concise (3-5 sentences)
- Address their specific concern
- Sign off as: {YOUR_NAME} from {YOUR_BUSINESS}
- Write ONLY the email body, no subject line, no labels
- Do not use bullet points"""
            }]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"  Groq error: {e}")
        return f"Thank you for reaching out. We have received your message and will get back to you shortly.\n\nBest regards,\n{YOUR_NAME} from {YOUR_BUSINESS}"

def send_reply(service, original_msg, reply_text, to_email, subject, thread_id):
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg["In-Reply-To"] = original_msg["id"]
    msg["References"] = original_msg["id"]
    msg.attach(MIMEText(reply_text, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw, "threadId": thread_id}).execute()
    print(f"  ✅ Reply SENT to {to_email}")

def save_draft(service, to_email, subject, reply_text, thread_id):
    msg = MIMEMultipart()
    msg["To"] = to_email
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    msg.attach(MIMEText(reply_text, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().drafts().create(userId="me", body={"message": {"raw": raw, "threadId": thread_id}}).execute()
    print(f"  📝 Draft SAVED for {to_email} — check Gmail Drafts folder")

def run_bot():
    print(f"""
╔══════════════════════════════════════════════╗
║  Gmail AI Bot is running! (Powered by Groq)
║  Mode   : {MODE.upper()}
║  Tone   : {BOT_TONE}
║  Checking every {CHECK_INTERVAL} seconds...
║  Press Ctrl+C to stop
╚══════════════════════════════════════════════╝
    """)

    service = get_gmail_service()
    replied_ids = load_replied_ids()

    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking inbox...")
            results = service.users().messages().list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=10).execute()
            messages = results.get("messages", [])

            if not messages:
                print("  📭 No new emails.")
            else:
                print(f"  📬 Found {len(messages)} unread email(s).")

            for msg_ref in messages:
                msg_id = msg_ref["id"]
                if msg_id in replied_ids:
                    continue

                msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                subject   = headers.get("Subject", "(no subject)")
                sender    = headers.get("From", "")
                thread_id = msg["threadId"]

                match = re.match(r"(.+?)\s*<(.+?)>", sender)
                if match:
                    sender_name  = match.group(1).strip().strip('"')
                    sender_email = match.group(2).strip()
                else:
                    sender_name  = sender
                    sender_email = sender

                print(f"\n  📧 From   : {sender_name} <{sender_email}>")
                print(f"     Subject: {subject[:60]}")

                if should_skip(sender_email, subject):
                    print(f"  ⏭️  Skipping (newsletter/no-reply)")
                    save_replied_id(msg_id)
                    replied_ids.add(msg_id)
                    continue

                body = get_email_body(msg["payload"])
                if not body:
                    print("  ⏭️  Skipping (empty body)")
                    save_replied_id(msg_id)
                    replied_ids.add(msg_id)
                    continue

                reply_text = generate_reply(sender_name, subject, body)

                if MODE == "auto":
                    send_reply(service, msg, reply_text, sender_email, subject, thread_id)
                elif MODE == "draft":
                    save_draft(service, sender_email, subject, reply_text, thread_id)
                elif MODE == "both":
                    save_draft(service, sender_email, subject, reply_text, thread_id)
                    send_reply(service, msg, reply_text, sender_email, subject, thread_id)

                service.users().messages().modify(userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()
                save_replied_id(msg_id)
                replied_ids.add(msg_id)

        except KeyboardInterrupt:
            print("\n\n👋 Bot stopped. Goodbye!")
            break
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print(f"\n  ⏳ Next check in {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_bot()
