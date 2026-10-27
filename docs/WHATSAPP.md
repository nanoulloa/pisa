# WhatsApp setup

The bot is built and tested against Meta's documented Graph API (v26.0). It stays off until
four values are set. Everything below is free: incoming messages cost nothing, and each
business number gets 1,000 free replies a month (a check uses two). Do not add a payment
method to the WhatsApp Business account, so nothing can be charged beyond that.

## 1. Create the app (Meta for Developers)

1. Go to https://developers.facebook.com/apps and create an app. Choose the use case for
   connecting with customers through WhatsApp, and name it Pisa.
2. When asked, create or pick a Meta Business portfolio. It is free. Skip payment methods.
3. In the app, open **WhatsApp > API Setup**. Meta gives you a test phone number. Copy its
   **Phone number ID**.
4. In **To**, add your own WhatsApp number and confirm it with the code Meta sends. The test
   number can reply to up to five confirmed numbers.

## 2. Get the access token and the app secret

- **Access token:** the one on the API Setup page lasts 24 hours, enough to try. For the demo,
  create a permanent one in Business settings > Users > System users:
  1. **Add** a system user (Pisa's is `pisa-bot`, with the Admin role).
  2. **Assign assets:** the Pisa app with full access, and the WhatsApp account with partial
     access: "Phone numbers (view and manage)" and "Messages". Skip "Everything": it also opens
     the payment information, which the bot never needs.
  3. **Generate token:** app Pisa, expiry "Never", and only `whatsapp_business_messaging` and
     `whatsapp_business_management`. Meta shows it once.

  Check it without printing it: Graph's `GET /debug_token` should report `type` `SYSTEM_USER`
  and `expires_at` 0.
- **App secret:** App settings > Basic > App secret > Show.
- **Verify token:** a random string you choose. Make one with:

  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(24))"
  ```

## 3. Put them in `.env`

| Line | Key |
|---|---|
| 23 | `WHATSAPP_ACCESS_TOKEN` |
| 24 | `WHATSAPP_PHONE_NUMBER_ID` |
| 25 | `WHATSAPP_BUSINESS_ACCOUNT_ID` (for the subscription step) |
| 27 | `WHATSAPP_APP_SECRET` |
| 29 | `WHATSAPP_WEBHOOK_VERIFY_TOKEN` |

Then copy them to the deployed engine and redeploy (only key names are printed):

```bash
make sync-secrets
```

```bash
make deploy-engine
```

## 4. Publish the app

Meta delivers real messages to the webhook only once the app is published; until then only
the dashboard's test events arrive. Publishing needs a privacy policy URL: App settings >
Basic > Privacy policy URL = `https://pisa-theta.vercel.app/en/privacy`, save, then
**Publish**. With the test number, still only the confirmed numbers can write to it.

## 5. Connect the webhook

In the app, open **WhatsApp > Configuration > Webhook**:

- **Callback URL:** `https://nanoulloa--pisa-engine-web.us-east.modal.run/whatsapp/webhook`
- **Verify token:** the same string as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.

Press **Verify and save**, then subscribe to the **messages** field.

Then subscribe the app to the WhatsApp Business account. The new dashboard may leave the
account subscribed only to Meta's own test tool, and then real messages never reach Pisa:

```bash
uv run python scripts/whatsapp_subscribe.py
```

It should list **Pisa** among the subscribed apps.

## 6. Try it

From your phone, write "hola" to the test number: Pisa answers with what it does. Then
forward a video where something falls, is thrown or bounces. Pisa acknowledges at once and
replies with the evidence video, the verdict and a link to the full result.

## How it works

- Every delivery is checked against `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with the
  app secret) before anything else; the endpoint answers at once and works in the background.
- Each message id is claimed once in Supabase (`whatsapp_messages`), because Meta retries
  deliveries and may send a message twice. Ids are forgotten after 7 days.
- Each number may start 20 checks an hour, within the engine's global hourly limit.
- The reply language comes from the message's own words when they show it, otherwise from
  the phone's country code.
- The phone number is used only to reply: jobs and results never store it, and logs carry a
  salted hash. The downloaded video and everything made from it are deleted after the reply.
