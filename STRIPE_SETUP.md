# Stripe Keys Setup Guide

This guide will help you find and configure your Stripe API keys and webhook secret for StatBox.

---

## 📍 Where to Find Your Stripe Keys

### Step 1: Access Stripe Dashboard

1. **Log in to Stripe**: https://dashboard.stripe.com
   - If you don't have an account, sign up at https://stripe.com

2. **Navigate to API Keys**:
   - In the left sidebar, click **"Developers"**
   - Click **"API keys"**

### Step 2: Find Your API Keys

You'll see two sections: **"Test mode"** and **"Live mode"**

#### For Development/Testing (Start Here)

**Test Mode Keys** (use these first to test without real charges):

1. Make sure **"Test mode"** toggle is ON (top right of screen)
2. You'll see:
   - **Publishable key**: Starts with `pk_test_...` 
     - This is your `STRIPE_PUBLIC_KEY`
   - **Secret key**: Click **"Reveal test key"** → Starts with `sk_test_...`
     - This is your `STRIPE_SECRET_KEY`

**Important**: Test mode uses fake cards. Test cards:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Use any future expiry date and any 3-digit CVC

#### For Production (After Testing)

**Live Mode Keys** (only use these for real payments):

1. Toggle **"Live mode"** ON (top right)
2. You'll see:
   - **Publishable key**: Starts with `pk_live_...`
     - This is your `STRIPE_PUBLIC_KEY` for production
   - **Secret key**: Click **"Reveal live key"** → Starts with `sk_live_...`
     - This is your `STRIPE_SECRET_KEY` for production

**⚠️ Security Warning**: 
- Never share your **Secret Key** (`sk_live_...` or `sk_test_...`)
- The **Publishable Key** (`pk_live_...` or `pk_test_...`) is safe to use in frontend code
- Never commit secret keys to Git - always use `.env` file

---

## 🔗 Setting Up Webhooks (For Webhook Secret)

Webhooks allow Stripe to notify your application about payment events (successful payments, cancellations, etc.).

### Step 1: Create a Webhook Endpoint

1. In Stripe Dashboard, go to **"Developers"** → **"Webhooks"**
2. Click **"Add endpoint"** or **"Add endpoint"**
3. Fill in:
   - **Endpoint URL**: 
     - For local testing: `http://localhost:8000/accounts/webhook/`
     - For production: `https://your-domain.com/accounts/webhook/`
   - **Description**: `StatBox Subscription Webhooks` (optional)
4. Click **"Add endpoint"**

### Step 2: Select Events to Listen To

After creating the endpoint, you'll see **"Select events to listen to"**:

**For StatBox, select these events**:
- `checkout.session.completed` - When payment is completed
- `customer.subscription.created` - When subscription is created
- `customer.subscription.updated` - When subscription is updated
- `customer.subscription.deleted` - When subscription is cancelled
- `invoice.payment_succeeded` - When recurring payment succeeds
- `invoice.payment_failed` - When payment fails

**Quick option**: Click **"Select all events"** to listen to everything (you can filter in code later)

5. Click **"Add events"**

### Step 3: Get Your Webhook Signing Secret

After creating the webhook:

1. Click on your webhook endpoint in the list
2. Look for **"Signing secret"** section
3. Click **"Reveal"** or **"Click to reveal"**
4. Copy the secret - it starts with `whsec_...`
   - This is your `STRIPE_WEBHOOK_SECRET`

**⚠️ Important**: 
- Each webhook endpoint has its own signing secret
- Test mode and Live mode have different webhooks and secrets
- Use test mode secret for development, live mode secret for production

---

## 🔧 Configuring Your Application

### For Local Development (Test Mode)

Edit your `.env` file:

```bash
# Stripe Settings (Test Mode)
STRIPE_PUBLIC_KEY=pk_test_your_actual_test_key_here
STRIPE_SECRET_KEY=sk_test_your_actual_test_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_test_webhook_secret_here
```

### For Production (Live Mode)

Edit your `.env` file on your production server:

```bash
# Stripe Settings (Live Mode)
STRIPE_PUBLIC_KEY=pk_live_your_actual_live_key_here
STRIPE_SECRET_KEY=sk_live_your_actual_live_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_live_webhook_secret_here
```

---

## 🧪 Testing Your Setup

### Test Mode Setup

1. Use test mode keys in your `.env`
2. Start your application
3. Try a test payment with card `4242 4242 4242 4242`
4. Check Stripe Dashboard → **"Payments"** → You should see test payments
5. Check your webhook logs in Dashboard → **"Developers"** → **"Webhooks"** → Click your endpoint → **"Logs"**

### Switching to Live Mode

**Only after thorough testing**:

1. Get live mode keys from Stripe Dashboard
2. Create a live mode webhook endpoint
3. Update production `.env` file with live keys
4. Test with a small real payment first

---

## 📋 Quick Reference: Key Formats

| Key Type | Test Mode Format | Live Mode Format |
|----------|------------------|------------------|
| Public Key | `pk_test_...` | `pk_live_...` |
| Secret Key | `sk_test_...` | `sk_live_...` |
| Webhook Secret | `whsec_...` | `whsec_...` |

**Note**: Webhook secrets look the same in test and live, but they're different values and must match the mode you're using.

---

## ❓ Common Questions

### Q: Do I need both test and live keys?

**A**: Yes, ideally:
- Use **test keys** for development and testing
- Use **live keys** for production (real customers)

### Q: Can I use test keys in production?

**A**: No. Test keys won't process real payments. You must use live keys for production.

### Q: What happens if I lose my secret key?

**A**: You can regenerate it in Stripe Dashboard → Developers → API keys → Click "..." → "Reveal key" → "Reveal test/live key"

### Q: My webhook isn't working. What's wrong?

**A**: Common issues:
1. Wrong webhook secret (check test vs live mode)
2. Wrong webhook URL (check it matches your endpoint)
3. SSL certificate issues (production must use HTTPS)
4. Firewall blocking Stripe's IPs
5. Webhook endpoint URL doesn't match exactly (no trailing slashes, correct path)

### Q: How do I test webhooks locally?

**A**: Use Stripe CLI (recommended):
```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
# Forward webhooks to localhost
stripe listen --forward-to localhost:8000/accounts/webhook/
# Stripe will give you a webhook signing secret - use that in your .env
```

Or use a tool like ngrok to expose your local server:
```bash
# Install ngrok, then:
ngrok http 8000
# Use the ngrok URL for your webhook endpoint
```

---

## 🔐 Security Best Practices

1. ✅ **Never commit keys to Git** - Always use `.env` file (already in `.gitignore`)
2. ✅ **Use test keys for development** - Never test with live keys
3. ✅ **Rotate keys if exposed** - If you accidentally commit a key, regenerate it immediately
4. ✅ **Use environment-specific keys** - Different keys for dev/staging/production
5. ✅ **Restrict API key permissions** - In Stripe Dashboard → Developers → API keys → Click key → Set restrictions
6. ✅ **Monitor API usage** - Check Stripe Dashboard regularly for suspicious activity

---

## 🚀 Next Steps

After setting up your Stripe keys:

1. ✅ Add keys to your `.env` file
2. ✅ Test with test mode keys first
3. ✅ Set up webhook endpoint
4. ✅ Test payment flow end-to-end
5. ✅ When ready, switch to live keys for production
6. ✅ Update webhook endpoint URL for production domain

---

## 📞 Additional Resources

- **Stripe Dashboard**: https://dashboard.stripe.com
- **Stripe API Documentation**: https://stripe.com/docs/api
- **Stripe Webhooks Guide**: https://stripe.com/docs/webhooks
- **Stripe Testing**: https://stripe.com/docs/testing
- **Stripe Support**: https://support.stripe.com

---

**Need Help?** Check your webhook logs in Stripe Dashboard → Developers → Webhooks → Your endpoint → Logs to see what events are being received and any errors.

