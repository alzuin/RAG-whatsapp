# WhatsApp Integration with Twilio

This module connects incoming WhatsApp messages (via Twilio) to an internal LLM-powered assistant and delivers intelligent replies back to the user over WhatsApp.

---

## 📲 Workflow

1. **User sends WhatsApp message** ➝ received by Twilio webhook
2. **Webhook endpoint** (`/whatsapp`) extracts sender and message content
3. **Message forwarded** to internal `/chat` API for LLM processing
4. **Reply received** and delivered back to user via Twilio

---

## 🔧 Endpoint

**`POST /whatsapp`** (FastAPI route)

### Expected Form Fields from Twilio:
- `From`: WhatsApp sender phone number (e.g. `whatsapp:+447123456789`)
- `Body`: The user's message content

### Internal Call:
Sends a POST request to the internal chat API:
```json
{
  "user_id": "447123456789",
  "message": "I'm looking for something interesting."
}
```

### Outgoing Message:
Sends the LLM's reply back to the user via Twilio's API:
- Uses `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER`
- Message sent using `https://api.twilio.com/2010-04-01/Accounts/.../Messages.json`

---

## 🔐 Auth
- Internal chat API: Optional `x-api-key` header
- Twilio: BasicAuth with account credentials

---

## 📝 Example .env
```
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
CHAT_API_URL=https://internal.api/chat
INTERNAL_API_KEY=optional-secret-key
```

---

## 📡 Twilio Setup
1. Create a WhatsApp-enabled sender in [Twilio Console](https://console.twilio.com/)
2. Set the webhook to your public endpoint (e.g. via API Gateway or Ngrok)
3. Deploy the FastAPI service with access to your `.env` or secret manager

---

## ✅ Status Codes
| Code | Meaning |
|------|---------|
| 200  | Reply sent successfully via Twilio |
| 400  | Missing `From` or `Body` in the incoming Twilio payload |
| 502  | Error calling internal chat API |
| 500  | Unexpected error in processing the webhook |

---

## 👤 Author
Made by [Alberto Zuin](https://moyd.co.uk) — powered by LLMs, Twilio, and FastAPI.

