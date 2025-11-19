# Landing Page Setup Guide

This guide explains how to create a landing page using the admin Page tool that dynamically displays subscription plans from your database.

## Quick Setup (Recommended)

### Option 1: Use the Management Command

1. Run the management command to automatically create the landing page:
   ```bash
   python manage.py create_landing_page
   ```

2. The command will:
   - Read `LANDING_PAGE_CONTENT.html`
   - Create a new Page with type "Landing Page"
   - Set it as the default landing page
   - Mark it as published

3. To update an existing landing page:
   ```bash
   python manage.py create_landing_page --update
   ```

### Option 2: Manual Setup via Admin

1. Go to **Admin → Pages → Add Page**

2. Fill in the form:
   - **Title**: "Landing Page" (or your preferred title)
   - **Slug**: "landing" (or leave blank for auto-generation)
   - **Page Type**: Select "Landing Page"
   - **Content**: Copy and paste the entire content from `LANDING_PAGE_CONTENT.html`
   - **Is Default Landing**: ✓ Check this box
   - **Is Published**: ✓ Check this box
   - **Allow Indexing**: ✓ Check this (for SEO)

3. Click **Save**

## How It Works

The landing page automatically:
- ✅ Reads subscription plans from **Admin → Subscription Plans**
- ✅ Displays all plans marked as `is_active=True`
- ✅ Shows plan names, prices, and features dynamically
- ✅ Updates automatically when you modify plans in the admin
- ✅ Falls back to a static "Free" plan if no plans exist

## Creating Subscription Plans

To see plans on the landing page:

1. Go to **Admin → Subscription Plans → Add Subscription Plan**

2. Fill in the plan details:
   - **Name**: e.g., "Free", "Basic", "Pro", "Enterprise"
   - **Price Monthly**: e.g., 0, 9.99, 29.99, 99.99
   - **Tier Key**: Select the tier (free, low, mid, high)
   - **Is Active**: ✓ Check this to display on landing page
   - **Features**: Add custom features (optional, JSON array)
   - **AI Features**: Add AI-related features (optional, JSON array)

3. Make sure **Is Active** is checked

4. The plan will automatically appear on the landing page!

## Features

- **Dynamic Pricing**: Plans update automatically when changed in admin
- **Responsive Design**: Works on mobile, tablet, and desktop
- **SEO Optimized**: Includes meta tags and proper structure
- **Modern UI**: Clean, professional design with smooth animations
- **Logo Support**: Automatically handles logo loading with fallback

## Troubleshooting

### Plans Not Showing

1. **Check if plans are active**:
   - Go to Admin → Subscription Plans
   - Ensure at least one plan has `Is Active` checked

2. **Check the page settings**:
   - Go to Admin → Pages
   - Find your landing page
   - Ensure `Is Default Landing` is checked
   - Ensure `Is Published` is checked

3. **Check server logs**:
   - Look for messages like "Found X active subscription plans"
   - Check for any template rendering errors

### Template Tags Not Working

If you see template tags like `{{ plan.name }}` instead of actual values:

1. Ensure the page content includes `{% load static %}` at the top
2. Check that the view is processing the template correctly
3. Verify plans exist in the database and are active

### Logo Not Loading

The landing page includes a fallback "GRA" text logo if the image doesn't load. To fix:

1. Ensure `engine/static/engine/logo.png` exists
2. Run `python manage.py collectstatic`
3. Check file permissions

## Customization

You can customize the landing page by:

1. Editing the page content in **Admin → Pages**
2. Modifying `LANDING_PAGE_CONTENT.html` and running `create_landing_page --update`
3. Adjusting CSS styles in the `<style>` section
4. Changing the featured plan (currently the 2nd plan)

## Notes

- The landing page uses Django template tags, so all `{% %}` and `{{ }}` syntax will be processed
- Plans are ordered by `price_monthly` (lowest first)
- The 2nd plan (if 2+ plans exist) is automatically marked as "Most Popular"
- The page automatically handles cases where no plans exist (shows fallback)

