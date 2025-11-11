# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for StatBox, allowing users to sign up and log in directly with their Google accounts.

## Prerequisites

- A Google Cloud Platform (GCP) account
- Access to Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter a project name (e.g., "StatBox")
5. Click "Create"

## Step 2: Enable Google+ API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API" or "Google Identity Services"
3. Click on it and click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in the required information:
     - App name: StatBox
     - User support email: your-email@example.com
     - Developer contact information: your-email@example.com
   - Add scopes: `email`, `profile`, `openid`
   - Add test users (if in testing mode) or publish the app
4. Back in Credentials, click "Create Credentials" > "OAuth client ID"
5. Choose application type: "Web application"
6. Name it (e.g., "StatBox Web Client")
7. Add authorized JavaScript origins:
   - For development: `http://localhost:8000`
   - For production: `https://yourdomain.com`
8. Add authorized redirect URIs:
   - For development: `http://localhost:8000/accounts/google/login/callback/`
   - For production: `https://yourdomain.com/accounts/google/login/callback/`
9. Click "Create"
10. Copy the **Client ID** and **Client Secret**

## Step 4: Configure Environment Variables

Add the following to your `.env` file:

```bash
# Google OAuth Credentials
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Site ID (required for allauth)
SITE_ID=1
```

## Step 5: Install Dependencies

```bash
pip install django-allauth
```

Or if using requirements files:

```bash
pip install -r requirements.txt
```

## Step 6: Run Migrations

Django-allauth requires database migrations:

```bash
python manage.py migrate
```

## Step 7: Create a Site in Django Admin

1. Go to Django admin: `http://localhost:8000/admin/`
2. Navigate to "Sites" > "Sites"
3. Edit the default site (or create a new one):
   - Domain name: `localhost:8000` (for development) or `yourdomain.com` (for production)
   - Display name: StatBox
4. Save

## Step 8: Test the Integration

1. Start your Django server
2. Go to the login page: `http://localhost:8000/accounts/login/`
3. Click "Continue with Google"
4. You should be redirected to Google's OAuth consent screen
5. After authorizing, you should be logged in

## Production Setup

For production:

1. Update the OAuth consent screen to "Published" status
2. Update authorized JavaScript origins and redirect URIs with your production domain
3. Update the Site in Django admin with your production domain
4. Ensure `SITE_ID` in settings matches your production site

## Troubleshooting

### "Redirect URI mismatch" error
- Make sure the redirect URI in Google Console exactly matches: `https://yourdomain.com/accounts/google/login/callback/`
- Check for trailing slashes and protocol (http vs https)

### "Access blocked" error
- Make sure the OAuth consent screen is published (or add test users if in testing mode)
- Check that all required scopes are added

### User profile not created
- Check that signals are properly registered in `accounts/apps.py`
- Verify the `UserProfile` model exists and migrations are run

### Email not verified
- Social accounts from Google are automatically verified (email is verified by Google)
- Regular signups still require email verification

## Security Notes

- Never commit your `GOOGLE_OAUTH_CLIENT_SECRET` to version control
- Use environment variables for all sensitive credentials
- Keep your OAuth credentials secure
- Regularly rotate your client secret if compromised

