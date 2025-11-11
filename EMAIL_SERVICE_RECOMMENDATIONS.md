# Affordable Email Service Recommendations for Django

This guide compares affordable transactional email services suitable for sending welcome emails, verification links, and password reset emails from your Django application.

## Top Recommendations

### 1. **Resend** ⭐ Best Overall (Recommended)
- **Free Tier**: 3,000 emails/month, 100 emails/day
- **Paid Plans**: Starting at $20/month for 50,000 emails
- **Pros**:
  - Modern API with excellent developer experience
  - Great documentation and Django support
  - Fast delivery
  - Clean dashboard
  - Good for startups and small apps
- **Cons**: Newer service (less established than competitors)
- **Best For**: Modern Django apps, startups, small to medium traffic
- **Website**: https://resend.com

### 2. **SendGrid** (Twilio)
- **Free Tier**: 100 emails/day forever
- **Paid Plans**: Starting at $19.95/month for 50,000 emails
- **Pros**:
  - Very established and reliable
  - Excellent deliverability
  - Great analytics and tracking
  - Good free tier for testing
  - Strong Django integration
- **Cons**: Can get expensive at scale
- **Best For**: Established apps, high deliverability needs
- **Website**: https://sendgrid.com

### 3. **Mailgun**
- **Free Tier**: 5,000 emails/month for 3 months, then 1,000 emails/month
- **Paid Plans**: Starting at $35/month for 50,000 emails
- **Pros**:
  - Excellent deliverability
  - Good for transactional emails
  - Strong API
  - Good documentation
- **Cons**: Free tier limited after 3 months
- **Best For**: Apps needing high deliverability
- **Website**: https://www.mailgun.com

### 4. **Postmark**
- **Free Tier**: 100 emails/month
- **Paid Plans**: Starting at $15/month for 10,000 emails
- **Pros**:
  - Excellent deliverability (99%+)
  - Great for transactional emails
  - Fast delivery
  - Good customer support
- **Cons**: More expensive per email than competitors
- **Best For**: Critical transactional emails (password resets, etc.)
- **Website**: https://postmarkapp.com

### 5. **Amazon SES** (AWS)
- **Free Tier**: 62,000 emails/month (if on EC2), otherwise pay-as-you-go
- **Paid Plans**: $0.10 per 1,000 emails (very cheap)
- **Pros**:
  - Extremely affordable at scale
  - Highly scalable
  - Reliable (AWS infrastructure)
  - Great for high volume
- **Cons**:
  - More complex setup
  - Requires AWS account
  - Less user-friendly dashboard
- **Best For**: High-volume apps, cost-sensitive projects
- **Website**: https://aws.amazon.com/ses/

### 6. **Brevo** (formerly Sendinblue)
- **Free Tier**: 300 emails/day
- **Paid Plans**: Starting at $25/month for 20,000 emails
- **Pros**:
  - Generous free tier
  - Good for both transactional and marketing emails
  - User-friendly interface
  - Good deliverability
- **Cons**: Can be slower than competitors
- **Best For**: Apps needing both transactional and marketing emails
- **Website**: https://www.brevo.com

## Comparison Table

| Service | Free Tier | Paid Starting | Best For |
|---------|-----------|---------------|----------|
| **Resend** | 3,000/month | $20/month | Modern apps, startups |
| **SendGrid** | 100/day | $19.95/month | Established apps |
| **Mailgun** | 1,000/month* | $35/month | High deliverability |
| **Postmark** | 100/month | $15/month | Critical emails |
| **Amazon SES** | 62k/month** | $0.10/1k | High volume |
| **Brevo** | 300/day | $25/month | Mixed use |

*After 3 months of 5,000/month  
**If on EC2, otherwise pay-as-you-go

## Recommendation for Your Project

### For Small/Startup Apps (< 1,000 emails/month):
**Resend** - Best balance of free tier, ease of use, and modern features

### For Growing Apps (1,000-10,000 emails/month):
**SendGrid** or **Resend** - Both offer good value and reliability

### For High-Volume Apps (> 10,000 emails/month):
**Amazon SES** - Most cost-effective at scale

### For Critical Emails (Password resets, etc.):
**Postmark** - Best deliverability, though more expensive

## Quick Setup Guide

### Option 1: Resend (Recommended)

1. Sign up at https://resend.com
2. Get your API key
3. Install: `pip install resend` (or use SMTP)
4. Update `.env`:
   ```bash
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.resend.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=resend
   EMAIL_HOST_PASSWORD=your-resend-api-key
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

### Option 2: SendGrid

1. Sign up at https://sendgrid.com
2. Create API key
3. Update `.env`:
   ```bash
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.sendgrid.net
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=apikey
   EMAIL_HOST_PASSWORD=your-sendgrid-api-key
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

### Option 3: Amazon SES

1. Set up AWS account
2. Verify your domain/email
3. Install: `pip install django-ses`
4. Update `settings.py`:
   ```python
   EMAIL_BACKEND = 'django_ses.SESBackend'
   AWS_SES_REGION_NAME = 'us-east-1'
   AWS_SES_REGION_ENDPOINT = 'email.us-east-1.amazonaws.com'
   AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
   AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
   ```

## Cost Comparison (10,000 emails/month)

- **Resend**: $20/month
- **SendGrid**: $19.95/month
- **Mailgun**: $35/month
- **Postmark**: $15/month
- **Amazon SES**: ~$1/month
- **Brevo**: $25/month

## Important Notes

1. **Domain Verification**: Most services require you to verify your sending domain for better deliverability
2. **SPF/DKIM Records**: Set up these DNS records to improve email deliverability
3. **Rate Limits**: Free tiers have daily/monthly limits
4. **Warm-up Period**: New accounts may need to "warm up" before sending at full capacity

## My Recommendation

For your StatBox application, I recommend **Resend** because:
- Generous free tier (3,000 emails/month)
- Modern, developer-friendly API
- Easy Django integration
- Good balance of features and cost
- Excellent for transactional emails

If you need more volume later, you can easily switch to Amazon SES for better cost efficiency.

