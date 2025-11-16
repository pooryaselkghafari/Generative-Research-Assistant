# Legal Documents Setup Guide

This guide explains how to set up the Privacy Policy and Terms of Service pages, along with the user agreement popup.

## What Was Created

1. **Privacy Policy Content** (`PRIVACY_POLICY_CONTENT.html`) - Comprehensive privacy policy covering:
   - Data collection and usage
   - Encryption standards (AES-256-GCM)
   - PIPEDA, CCPA/CPRA, HIPAA compliance
   - User rights and data retention

2. **Terms of Service Content** (`TERMS_OF_SERVICE_CONTENT.html`) - Complete terms of service covering:
   - User accounts and security
   - Acceptable use policies
   - Data ownership and rights
   - Subscription and payment terms
   - Liability and termination

3. **User Agreement Popup** - Added to registration page (`accounts/templates/accounts/register.html`):
   - Shows before user can register
   - Highlights key privacy and security features
   - Links to full Privacy Policy and Terms of Service
   - Requires explicit agreement checkbox

4. **Management Command** (`engine/management/commands/create_legal_documents.py`) - Automatically creates the documents in the database

## Setup Instructions

### Step 1: Create the Legal Documents in Database

Run the management command to create the Privacy Policy and Terms of Service:

```bash
python manage.py create_legal_documents
```

This will:
- Read the content from `PRIVACY_POLICY_CONTENT.html` and `TERMS_OF_SERVICE_CONTENT.html`
- Create or update Privacy Policy v1.0 in the database
- Create or update Terms of Service v1.0 in the database

### Step 2: Verify the Documents

1. **Check Django Admin:**
   - Go to `/admin/engine/privacypolicy/`
   - Go to `/admin/engine/termsofservice/`
   - Verify the documents are created and marked as active

2. **View the Pages:**
   - Privacy Policy: `/privacy/`
   - Terms of Service: `/terms/`

### Step 3: Test the Registration Popup

1. Go to the registration page: `/accounts/register/`
2. You should see a modal popup with:
   - User Agreement & Privacy Policy header
   - Key points about encryption and compliance
   - Links to full documents
   - Checkbox to agree
   - "I Agree & Continue" button (disabled until checkbox is checked)

3. Test the flow:
   - Check the agreement checkbox
   - Click "I Agree & Continue"
   - The form should appear
   - Try registering a test account

### Step 4: Customize Content (Optional)

To customize the content:

1. **Edit the HTML files:**
   - Edit `PRIVACY_POLICY_CONTENT.html` for privacy policy
   - Edit `TERMS_OF_SERVICE_CONTENT.html` for terms of service

2. **Update in database:**
   - Either run `python manage.py create_legal_documents` again
   - Or edit directly in Django Admin

3. **Update contact information:**
   - Replace `[Your Company Address]` with your actual address
   - Replace `privacy@statbox.com` and `legal@statbox.com` with your email addresses
   - Update jurisdiction in "Governing Law" section

## Features

### User Agreement Popup

- **Appears before registration** - Users must agree before they can see the registration form
- **Session-based** - Agreement is stored in `sessionStorage`, so it persists during the session
- **Responsive design** - Works on mobile and desktop
- **Smooth animations** - Fade-in and slide-up animations
- **Links to full documents** - Opens in new tabs

### Privacy Policy Highlights

- AES-256-GCM encryption
- PIPEDA compliance (Canada)
- CCPA/CPRA compliance (California, USA)
- HIPAA compliance (health data)
- Data encryption at rest
- User-specific encryption keys
- Admin activity logging

### Terms of Service Highlights

- Account security requirements
- Acceptable use policies
- Data ownership rights
- Subscription and payment terms
- Termination policies
- Liability limitations

## URLs

- Privacy Policy: `/privacy/`
- Terms of Service: `/terms/`
- Registration (with popup): `/accounts/register/`

## Admin Interface

You can manage the documents in Django Admin:

1. Go to `/admin/engine/privacypolicy/`
2. Go to `/admin/engine/termsofservice/`

You can:
- Create new versions
- Edit content
- Set effective dates
- Activate/deactivate versions

## Updating Documents

### Method 1: Management Command (Recommended)

1. Edit the HTML content files
2. Run: `python manage.py create_legal_documents`

### Method 2: Django Admin

1. Go to Django Admin
2. Edit the Privacy Policy or Terms of Service
3. Update the content directly in the rich text editor
4. Save

### Method 3: Create New Version

1. In Django Admin, create a new Privacy Policy or Terms of Service
2. Set a new version number (e.g., "1.1")
3. Set the effective date
4. Mark the old version as inactive
5. Mark the new version as active

## Testing

To test the complete flow:

1. **Clear browser session storage:**
   ```javascript
   sessionStorage.clear();
   ```

2. **Visit registration page:**
   - Should show popup
   - Should hide registration form

3. **Agree to terms:**
   - Check checkbox
   - Click "I Agree & Continue"
   - Form should appear

4. **Try to submit without agreeing:**
   - Form submission should be blocked
   - Popup should reappear

## Notes

- The popup uses `sessionStorage` to remember agreement during the session
- If user closes browser, they'll need to agree again (by design)
- The popup cannot be bypassed - users must agree to register
- Links to full documents open in new tabs
- The popup is responsive and works on mobile devices

## Troubleshooting

### Popup doesn't appear
- Check browser console for JavaScript errors
- Verify `register.html` template is being used
- Check that `sessionStorage` is available (modern browsers)

### Documents don't show
- Run `python manage.py create_legal_documents`
- Check Django Admin to verify documents are active
- Verify URLs are correct: `/privacy/` and `/terms/`

### Content doesn't update
- Clear browser cache
- Run the management command again
- Check that documents are marked as active in admin

