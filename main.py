import logging
import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from httpx import AsyncClient, HTTPError, BasicAuth
from mangum import Mangum

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI()

# Chat API config
CHAT_API_URL = os.getenv("CHAT_API_URL", "https://xxxxxx.execute-api.eu-west-2.amazonaws.com/prod/chat-api/message")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# Twilio config
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """
    Handles incoming WhatsApp messages via Twilio webhook and routes them to the internal chat API.

    Workflow:
    1. Parses the incoming form payload from Twilio (expects 'From' and 'Body').
    2. Sends the user's message and ID to an internal chat API for processing.
    3. Receives a reply from the internal LLM-powered chat system.
    4. Sends the reply back to the user via Twilio's WhatsApp API.

    Args:
        request (Request): A FastAPI-compatible incoming HTTP request object.

    Returns:
        JSONResponse: A response indicating success (200 OK) or error (4xx/5xx).

    Error Handling:
        - Returns 400 if required fields are missing from the incoming Twilio payload.
        - Returns 502 if the internal chat API call fails.
        - Returns 500 for any unexpected exceptions.
    """
    try:
        form_data = await request.form()

        from_number = form_data.get("From", "").strip().replace(" ", "")
        body = form_data.get("Body")

        if not from_number or not body:
            logger.warning("Missing required fields in Twilio payload")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": "Invalid payload"})

        user_id = from_number.replace("whatsapp:", "")
        logger.info(f"Received WhatsApp message from {user_id}: {body}")

        # Call internal chat API
        async with AsyncClient() as client:
            chat_response = await client.post(
                CHAT_API_URL,
                json={"user_id": user_id, "message": body},
                headers={"Content-Type": "application/json", "x-api-key": INTERNAL_API_KEY} if INTERNAL_API_KEY else None,
                timeout=20.0,
            )

        chat_response.raise_for_status()
        reply_data = chat_response.json()
        reply_message = reply_data.get("reply", "I'm not sure how to reply to that.")
        logger.info(f"Sending reply to WhatsApp number: {from_number!r}")
        logger.info(f"Reply from chat-api: {reply_message}")

        # Send reply back to WhatsApp user via Twilio API
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        payload = {
            "From": TWILIO_WHATSAPP_NUMBER,
            "To": from_number,
            "Body": reply_message
        }

        logger.info(f"Twilio Payload: {payload}")
        try:
            async with AsyncClient() as client:
                twilio_response = await client.post(
                    twilio_url,
                    data=payload,
                    auth=BasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                    timeout=10.0,
                )
                twilio_response.raise_for_status()
        except HTTPError as e:
            error_details = e.response.text if e.response else "No response body"
            logger.error(f"HTTP error: {e.response.status_code if e.response else 'No status'} - {error_details}")

        logger.info(f"Message sent to user via Twilio: {twilio_response.text}")

        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "replied"})

    except HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"error": "Upstream service error"})

    except Exception as e:
        logger.exception("Unexpected error in WhatsApp webhook")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Internal server error"})

handler = Mangum(app)