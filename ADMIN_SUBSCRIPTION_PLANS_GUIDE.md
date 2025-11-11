# Admin Guide: Adding Subscription Plans to Landing Page

## Overview
You can now dynamically insert subscription plans into your landing page content using the CKEditor. The plans will automatically update whenever you modify them in the admin panel.

## How to Use

### Method 1: Using the Button (Recommended)

1. **Go to Admin Panel** → **Pages** → Edit your landing page
2. **In the Content Editor**, place your cursor where you want the subscription plans to appear
3. **Click the "Insert Subscription Plans" button** in the CKEditor toolbar
   - Look for a button with a price tag icon or "Subscription Plans" label
   - It should be in the "Insert" section of the toolbar
4. **Save the page** - The subscription plans will automatically render when the page is viewed

### Method 2: Manual Insertion

If the button doesn't appear, you can manually add the code:

1. **Switch to "Source" view** in CKEditor (click the "Source" button)
2. **Insert this code** where you want the plans to appear:
   ```django
   {% load subscription_tags %}
   {% subscription_plans %}
   ```
3. **Switch back to visual editor** and save

## Customization Options

### Change Featured Plan
By default, the second plan (index 2) is marked as "Most Popular". To change this:

```django
{% subscription_plans featured_plan_index=3 %}
```

This will make the third plan featured instead.

## How It Works

1. **Template Tag**: The `{% subscription_plans %}` tag queries your database for all active `SubscriptionPlan` objects
2. **Automatic Updates**: When you modify plans in the admin (prices, features, limits), the landing page automatically reflects these changes
3. **Styling**: The plans are styled with a responsive grid layout that adapts to screen size
4. **Data Source**: Plans pull data from:
   - `SubscriptionPlan` model: name, price, features, AI features
   - `SubscriptionTierSettings` model: max datasets, sessions, file size limits

## Troubleshooting

### Button Not Appearing
- Make sure CKEditor is installed: `pip install django-ckeditor`
- Check that the plugin file exists at: `engine/static/engine/ckeditor_plugins/subscription_plans/plugin.js`
- Clear browser cache and refresh the admin page
- Check browser console for JavaScript errors

### Plans Not Displaying
- Verify you have active subscription plans in the admin (Pages → Subscription Plans)
- Check that plans have `is_active=True`
- View page source to see if the template tag is present
- Check Django server logs for template rendering errors

### Template Tag Not Rendering
- Make sure the page content contains `{% load subscription_tags %}` before using the tag
- Verify the `subscription_tags.py` file exists in `engine/templatetags/`
- Check that the page is being processed through the template engine (see `engine/views.py`)

## Technical Details

- **Template Tag Location**: `engine/templatetags/subscription_tags.py`
- **Widget Template**: `engine/templates/engine/subscription_plans_widget.html`
- **CKEditor Plugin**: `engine/static/engine/ckeditor_plugins/subscription_plans/plugin.js`
- **View Processing**: `engine/views.py` → `landing_view()` function processes template tags in page content

## Example Usage in CKEditor

When you click the button, this code is inserted:

```html
<div class="subscription-plans-placeholder">...</div>
{% load subscription_tags %}
{% subscription_plans %}
```

The placeholder div is just for visual reference in the editor. The actual rendering happens when the page is viewed.

