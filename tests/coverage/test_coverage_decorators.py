"""
Coverage tests for decorators.
"""
from django.test import Client, RequestFactory
from django.contrib.auth.models import User
from django.http import JsonResponse
from engine.models import Dataset, UserProfile
from engine.decorators import require_authentication, require_user_ownership, require_post_method
from tests.base import BaseTestSuite


class CoverageDecoratorsTestSuite(BaseTestSuite):
    category = 'coverage'
    test_name = 'Coverage - Decorators'
    target_score = 80.0
    
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user('decuser', 'dec@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'subscription_type': 'free'})
        profile.subscription_type = 'free'
        profile.save()
    
    def test_require_authentication_unauthenticated_ajax(self):
        """Test require_authentication decorator with unauthenticated AJAX request."""
        from django.contrib.auth.models import AnonymousUser
        
        @require_authentication
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = AnonymousUser()
        request.headers = {'X-Requested-With': 'XMLHttpRequest'}
        
        response = test_view(request)
        self.record_test(
            'require_authentication_unauthenticated_ajax',
            response.status_code == 401,
            f"Should return 401 for unauthenticated AJAX (got {response.status_code})"
        )
    
    def test_require_authentication_unauthenticated_regular(self):
        """Test require_authentication decorator with unauthenticated regular request."""
        from django.contrib.auth.models import AnonymousUser
        
        @require_authentication
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = AnonymousUser()
        request.headers = {}
        
        response = test_view(request)
        self.record_test(
            'require_authentication_unauthenticated_regular',
            response.status_code == 302,  # Redirect to login
            f"Should redirect to login for unauthenticated request (got {response.status_code})"
        )
    
    def test_require_authentication_authenticated(self):
        """Test require_authentication decorator with authenticated user."""
        @require_authentication
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = self.user
        
        response = test_view(request)
        self.record_test(
            'require_authentication_authenticated',
            response.status_code == 200,
            f"Should allow authenticated user (got {response.status_code})"
        )
    
    def test_require_user_ownership_valid(self):
        """Test require_user_ownership decorator with valid ownership."""
        dataset = Dataset.objects.create(
            user=self.user,
            name='Test Dataset',
            file_path='/test/path.csv'
        )
        
        @require_user_ownership(Dataset)
        def test_view(request, pk, _owned_object=None):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = self.user
        
        response = test_view(request, pk=dataset.id)
        self.record_test(
            'require_user_ownership_valid',
            response.status_code == 200,
            f"Should allow access to own dataset (got {response.status_code})"
        )
    
    def test_require_user_ownership_invalid(self):
        """Test require_user_ownership decorator with invalid ownership."""
        other_user = User.objects.create_user('other', 'other@test.com', 'pass123')
        dataset = Dataset.objects.create(
            user=other_user,
            name='Other Dataset',
            file_path='/test/path.csv'
        )
        
        @require_user_ownership(Dataset)
        def test_view(request, pk):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = self.user
        
        response = test_view(request, pk=dataset.id)
        self.record_test(
            'require_user_ownership_invalid',
            response.status_code == 404,
            f"Should return 404 for other user's dataset (got {response.status_code})"
        )
    
    def test_require_user_ownership_no_id(self):
        """Test require_user_ownership decorator without object ID."""
        @require_user_ownership(Dataset)
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        request.user = self.user
        
        response = test_view(request)
        self.record_test(
            'require_user_ownership_no_id',
            response.status_code == 400,
            f"Should return 400 when object ID missing (got {response.status_code})"
        )
    
    def test_require_post_method_post(self):
        """Test require_post_method decorator with POST."""
        @require_post_method
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.post('/test/')
        response = test_view(request)
        self.record_test(
            'require_post_method_post',
            response.status_code == 200,
            f"Should allow POST method (got {response.status_code})"
        )
    
    def test_require_post_method_get(self):
        """Test require_post_method decorator with GET."""
        @require_post_method
        def test_view(request):
            return JsonResponse({'success': True})
        
        request = self.factory.get('/test/')
        response = test_view(request)
        self.record_test(
            'require_post_method_get',
            response.status_code == 405,
            f"Should return 405 for non-POST method (got {response.status_code})"
        )

