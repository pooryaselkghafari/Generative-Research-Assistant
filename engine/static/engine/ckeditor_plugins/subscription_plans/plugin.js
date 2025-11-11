/**
 * CKEditor plugin to insert subscription plans placeholder
 * Place this file at: engine/static/engine/ckeditor_plugins/subscription_plans/plugin.js
 */
CKEDITOR.plugins.add('subscription_plans', {
    icons: 'subscription_plans',
    init: function(editor) {
        // Add button to toolbar
        editor.ui.addButton('SubscriptionPlans', {
            label: 'Insert Subscription Plans',
            command: 'insertSubscriptionPlans',
            toolbar: 'insert',
            icon: this.path + 'icons/subscription_plans.png' // Fallback to text if icon not found
        });

        // Define the command
        editor.addCommand('insertSubscriptionPlans', {
            exec: function(editor) {
                // Insert the template tag
                var html = '<div class="subscription-plans-placeholder" style="background: #f0f9ff; border: 2px dashed #0f6b72; padding: 20px; margin: 20px 0; text-align: center; border-radius: 8px;">' +
                          '<p style="margin: 0; color: #0f6b72; font-weight: 600;">📋 Subscription Plans Section</p>' +
                          '<p style="margin: 5px 0 0 0; color: #6b7280; font-size: 12px;">This will be replaced with dynamic subscription plans from your database</p>' +
                          '</div>' +
                          '{% load subscription_tags %}\n{% subscription_plans %}';
                editor.insertHtml(html);
            }
        });
    }
});

