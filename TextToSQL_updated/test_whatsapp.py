from fastapi import FastAPI, Form
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.getenv("TWILIO_WHATSAPP_FROM")


def send_whatsapp_message(to, message):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"

    data = {
        "From": FROM_NUMBER,
        "To": to,
        "Body": message
    }

    response = requests.post(url, data=data, auth=(TWILIO_SID, TWILIO_TOKEN))
    return response.json()


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    reply = f"fxiiisssss said: {Body}"
    print(f"Sending reply to {From}: {reply}")
    send_whatsapp_message(From, reply)
    return "OK"
