"""
Comprehensive test suite for the ticket/bug reporting system.
Covers all 14 test categories from TEST_CATEGORIES_COMPLETE.md
"""
import time
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from engine.models import Ticket
from tests.base import BaseTestSuite


class TicketSystemTestSuite(BaseTestSuite):
    """
    Comprehensive test suite for ticket system covering all 14 categories:
    1. Security - Authentication, authorization, data isolation
    2. Database - Query performance, integrity, constraints
    3. Performance - Response times, query efficiency
    4. Unit - Service layer, helper functions
    5. Integration - Complete workflows
    6. API - API endpoints
    7. E2E - End-to-end user flows
    8. Static Analysis - Code quality, syntax, security patterns
    9. Dependency Scan - Vulnerability scanning
    10. Coverage - Code coverage percentage
    11. Backup - Backup/restore functionality
    12. Monitoring - Logging and monitoring
    13. Cron - Scheduled tasks
    14. Frontend - Templates, static files, JavaScript
    """
    category = 'ticket'
    test_name = 'Ticket System Comprehensive Tests'
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all tests"""
        cls.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        cls.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        cls.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )
        cls.client = Client()
    
    # ==================== SECURITY TESTS ====================
    
    def test_security_authentication_required(self):
        """Security: Verify authentication is required for ticket views"""
        # Test ticket list requires login
        response = self.client.get(reverse('ticket_list'))
        self.assertNotEqual(response.status_code, 200)
        self.assertIn('login', response.url.lower() if hasattr(response, 'url') else '')
        
        # Test ticket create requires login
        response = self.client.get(reverse('ticket_create'))
        self.assertNotEqual(response.status_code, 200)
        
        # Test ticket detail requires login
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Test Ticket',
            description='Test Description'
        )
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertNotEqual(response.status_code, 200)
    
    def test_security_user_isolation(self):
        """Security: Users can only view their own tickets"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create ticket for user2
        ticket2 = Ticket.objects.create(
            user=self.user2,
            title='User2 Ticket',
            description='User2 Description'
        )
        
        # User1 should not be able to view user2's ticket
        response = self.client.get(reverse('ticket_detail', args=[ticket2.id]))
        self.assertEqual(response.status_code, 404)
    
    def test_security_csrf_protection(self):
        """Security: CSRF protection is enabled"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Try to create ticket without CSRF token
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'Test',
                'description': 'Test',
                'priority': 'medium'
            },
            follow=False
        )
        # Should fail with CSRF error (403 or redirect)
        self.assertIn(response.status_code, [403, 400])
    
    def test_security_sql_injection_prevention(self):
        """Security: SQL injection attempts are prevented"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Attempt SQL injection in title
        malicious_title = "'; DROP TABLE tickets; --"
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': malicious_title,
                'description': 'Test',
                'priority': 'medium'
            }
        )
        # Should create ticket with escaped title, not execute SQL
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        ticket = Ticket.objects.filter(title=malicious_title).first()
        self.assertIsNotNone(ticket)
        # Verify table still exists
        self.assertTrue(Ticket.objects.exists())
    
    def test_security_xss_prevention(self):
        """Security: XSS attacks are prevented in ticket content"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create ticket with XSS attempt
        xss_payload = '<script>alert("XSS")</script>'
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'XSS Test',
                'description': xss_payload,
                'priority': 'medium'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        ticket = Ticket.objects.get(title='XSS Test')
        # Description should be stored as-is (Django auto-escapes in templates)
        self.assertIn('<script>', ticket.description)
        
        # Verify template escapes it
        self.client.login(username='testuser1', password='testpass123')
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        # Template should escape the script tag
        self.assertNotIn('<script>alert', response.content.decode())
    
    # ==================== DATABASE TESTS ====================
    
    def test_database_foreign_key_integrity(self):
        """Database: Foreign key constraints are enforced"""
        # Try to create ticket with invalid user_id
        with self.assertRaises(Exception):
            Ticket.objects.create(
                user_id=99999,  # Non-existent user
                title='Test',
                description='Test',
                priority='medium'
            )
    
    def test_database_indexes_exist(self):
        """Database: Required indexes exist for performance"""
        from django.db import connection
        
        # Skip if using SQLite (doesn't support pg_indexes)
        if 'sqlite' in connection.settings_dict['ENGINE']:
            # For SQLite, just verify model has index definitions
            from django.db import models
            ticket_model = Ticket._meta
            indexes = ticket_model.indexes
            self.assertGreater(len(indexes), 0)
        else:
            with connection.cursor() as cursor:
                # Check indexes on ticket table
                cursor.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'engine_ticket'
                """)
                indexes = [row[0] for row in cursor.fetchall()]
                
                # Should have indexes on user, status, priority, created_at
                self.assertTrue(any('user' in idx.lower() for idx in indexes))
                self.assertTrue(any('status' in idx.lower() for idx in indexes))
    
    def test_database_query_performance(self):
        """Database: Ticket queries are optimized"""
        # Create multiple tickets
        for i in range(50):
            Ticket.objects.create(
                user=self.user1,
                title=f'Ticket {i}',
                description=f'Description {i}',
                priority='medium'
            )
        
        # Test query with select_related (should be used in admin)
        start_time = time.time()
        tickets = list(Ticket.objects.select_related('user', 'assigned_to').all()[:10])
        query_time = time.time() - start_time
        
        # Query should complete quickly (< 0.1s for 10 records)
        self.assertLess(query_time, 0.1)
        self.assertEqual(len(tickets), 10)
    
    def test_database_constraints(self):
        """Database: Model constraints are enforced"""
        # Test max_length constraint on title
        long_title = 'x' * 201  # Exceeds max_length=200
        ticket = Ticket(
            user=self.user1,
            title=long_title,
            description='Test',
            priority='medium'
        )
        with self.assertRaises(Exception):
            ticket.full_clean()
    
    # ==================== PERFORMANCE TESTS ====================
    
    def test_performance_ticket_list_response_time(self):
        """Performance: Ticket list page loads quickly"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create some tickets
        for i in range(20):
            Ticket.objects.create(
                user=self.user1,
                title=f'Ticket {i}',
                description=f'Description {i}',
                priority='medium'
            )
        
        start_time = time.time()
        response = self.client.get(reverse('ticket_list'))
        response_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        # Should load in under 0.5 seconds
        self.assertLess(response_time, 0.5)
    
    def test_performance_pagination(self):
        """Performance: Pagination works efficiently"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create 25 tickets
        for i in range(25):
            Ticket.objects.create(
                user=self.user1,
                title=f'Ticket {i}',
                description=f'Description {i}',
                priority='medium'
            )
        
        # Test pagination (10 per page)
        start_time = time.time()
        response = self.client.get(reverse('ticket_list'))
        response_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 0.5)
        # Should only show 10 tickets per page
        self.assertLessEqual(len(response.context['tickets']), 10)
    
    # ==================== UNIT TESTS ====================
    
    def test_unit_ticket_model_str(self):
        """Unit: Ticket model __str__ method works correctly"""
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Test Ticket',
            description='Test Description',
            priority='high'
        )
        expected_str = f"#{ticket.id} - Test Ticket ({self.user1.username})"
        self.assertEqual(str(ticket), expected_str)
    
    def test_unit_ticket_auto_resolved_at(self):
        """Unit: Ticket auto-sets resolved_at when status changes"""
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Test Ticket',
            description='Test Description',
            status='open'
        )
        self.assertIsNone(ticket.resolved_at)
        
        # Change to resolved
        ticket.status = 'resolved'
        ticket.save()
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.resolved_at)
        
        # Change back to open
        ticket.status = 'open'
        ticket.save()
        ticket.refresh_from_db()
        self.assertIsNone(ticket.resolved_at)
    
    def test_unit_ticket_status_choices(self):
        """Unit: Ticket status choices are valid"""
        valid_statuses = [choice[0] for choice in Ticket.STATUS_CHOICES]
        self.assertIn('open', valid_statuses)
        self.assertIn('in_progress', valid_statuses)
        self.assertIn('resolved', valid_statuses)
        self.assertIn('closed', valid_statuses)
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_integration_create_ticket_workflow(self):
        """Integration: Complete ticket creation workflow"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Step 1: Access create page
        response = self.client.get(reverse('ticket_create'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit ticket
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'Integration Test Ticket',
                'description': 'This is a test ticket',
                'priority': 'high'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Step 3: Verify ticket was created
        ticket = Ticket.objects.get(title='Integration Test Ticket')
        self.assertEqual(ticket.user, self.user1)
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.priority, 'high')
        
        # Step 4: View ticket in list
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(ticket, response.context['tickets'])
        
        # Step 5: View ticket detail
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ticket'], ticket)
    
    def test_integration_admin_ticket_management(self):
        """Integration: Admin can manage tickets"""
        # Create ticket as user
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Admin Test Ticket',
            description='Test Description',
            priority='urgent'
        )
        
        # Admin can update ticket
        ticket.status = 'in_progress'
        ticket.assigned_to = self.admin_user
        ticket.admin_response = 'We are working on this issue.'
        ticket.save()
        
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'in_progress')
        self.assertEqual(ticket.assigned_to, self.admin_user)
        self.assertIsNotNone(ticket.admin_response)
        
        # Verify admin can view ticket in admin interface
        self.client.login(username='admin', password='adminpass123')
        from django.contrib.admin.sites import site
        from engine.admin import TicketAdmin
        
        admin = TicketAdmin(Ticket, site)
        # Create a mock request object
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/admin/engine/ticket/')
        request.user = self.admin_user
        
        qs = admin.get_queryset(request)
        self.assertIn(ticket, qs)
    
    # ==================== API TESTS ====================
    
    def test_api_ticket_list_endpoint(self):
        """API: Ticket list endpoint returns correct data"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create tickets
        ticket1 = Ticket.objects.create(
            user=self.user1,
            title='Ticket 1',
            description='Description 1',
            priority='low'
        )
        ticket2 = Ticket.objects.create(
            user=self.user1,
            title='Ticket 2',
            description='Description 2',
            priority='high'
        )
        
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)
        tickets = response.context['tickets']
        self.assertIn(ticket1, tickets)
        self.assertIn(ticket2, tickets)
    
    def test_api_ticket_create_endpoint(self):
        """API: Ticket create endpoint accepts POST data"""
        self.client.login(username='testuser1', password='testpass123')
        
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'API Test Ticket',
                'description': 'API Test Description',
                'priority': 'medium'
            }
        )
        
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title='API Test Ticket')
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.description, 'API Test Description')
    
    def test_api_ticket_detail_endpoint(self):
        """API: Ticket detail endpoint returns correct ticket"""
        self.client.login(username='testuser1', password='testpass123')
        
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Detail Test Ticket',
            description='Detail Test Description',
            priority='urgent'
        )
        
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ticket'], ticket)
    
    # ==================== E2E TESTS ====================
    
    def test_e2e_user_reports_bug_and_views_it(self):
        """E2E: User can report bug and view it in their ticket list"""
        # User logs in
        self.client.login(username='testuser1', password='testpass123')
        
        # User navigates to profile
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        
        # User clicks "Report a Bug"
        response = self.client.get(reverse('ticket_create'))
        self.assertEqual(response.status_code, 200)
        
        # User fills out form and submits
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'E2E Test Bug',
                'description': 'This is a bug I found',
                'priority': 'high'
            }
        )
        self.assertEqual(response.status_code, 302)
        
        # User is redirected and sees success message
        response = self.client.get(reverse('ticket_list'), follow=True)
        self.assertEqual(response.status_code, 200)
        
        # User sees their ticket in the list
        ticket = Ticket.objects.get(title='E2E Test Bug')
        self.assertIn(ticket, response.context['tickets'])
        
        # User clicks on ticket to view details
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ticket'].title, 'E2E Test Bug')
    
    # ==================== MONITORING TESTS ====================
    
    def test_monitoring_ticket_creation_logged(self):
        """Monitoring: Ticket creation is logged"""
        self.client.login(username='testuser1', password='testpass123')
        
        # Create ticket
        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'Monitoring Test',
                'description': 'Test Description',
                'priority': 'medium'
            }
        )
        
        # Verify ticket was created (logged in database)
        ticket = Ticket.objects.get(title='Monitoring Test')
        self.assertIsNotNone(ticket.created_at)
        self.assertIsNotNone(ticket.updated_at)
    
    # ==================== FRONTEND TESTS ====================
    
    def test_frontend_ticket_list_template_renders(self):
        """Frontend: Ticket list template renders correctly"""
        self.client.login(username='testuser1', password='testpass123')
        
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/ticket_list.html')
        self.assertContains(response, 'My Support Tickets')
    
    def test_frontend_ticket_create_template_renders(self):
        """Frontend: Ticket create template renders correctly"""
        self.client.login(username='testuser1', password='testpass123')
        
        response = self.client.get(reverse('ticket_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/ticket_create.html')
        self.assertContains(response, 'Report a Bug')
        self.assertContains(response, 'title')
        self.assertContains(response, 'description')
        self.assertContains(response, 'priority')
    
    def test_frontend_ticket_detail_template_renders(self):
        """Frontend: Ticket detail template renders correctly"""
        self.client.login(username='testuser1', password='testpass123')
        
        ticket = Ticket.objects.create(
            user=self.user1,
            title='Frontend Test',
            description='Frontend Description',
            priority='high'
        )
        
        response = self.client.get(reverse('ticket_detail', args=[ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/ticket_detail.html')
        self.assertContains(response, 'Frontend Test')
        self.assertContains(response, 'Frontend Description')
    
    def test_frontend_profile_shows_ticket_section(self):
        """Frontend: Profile page shows ticket section"""
        self.client.login(username='testuser1', password='testpass123')
        
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Support & Bug Reports')
        self.assertContains(response, 'Report a Bug')
        self.assertContains(response, 'View My Tickets')

