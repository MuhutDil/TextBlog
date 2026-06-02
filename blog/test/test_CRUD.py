from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from unittest.mock import Mock, patch
from django.contrib import messages
 
from blog.models import Post
from blog.forms import PostForm
from blog.views import user_is_author, post_create, post_update, post_delete

from django.contrib.messages.storage.fallback import FallbackStorage


User = get_user_model()
 
class UserIsAuthorDecoratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.author = User.objects.create_user(
            email='author.email.com',
            username='author',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            email='other.email.com',
            username='other',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=cls.author,
            publish=timezone.now()
        )
 
    def test_author_can_access_view(self):
        """Test that the post author can access the decorated view"""
        request = self.factory.get('/fake-url')
        request.user = self.author
        
        @user_is_author
        def test_view(request, post_id, post):
            return "success"
        
        result = test_view(request, post_id=self.post.id)
        self.assertEqual(result, "success")
 
    def test_non_author_redirected_with_error_message(self):
        
        """Test that non-author is redirected with error message"""
        request = self.factory.get('/fake-url')
        request.user = self.other_user

        # Fix message error
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        @user_is_author
        def test_view(request, post_id, post):
            return "success"
        
        response = test_view(request, post_id=self.post.id)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.post.get_absolute_url())
        
        # Check error message
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "You don't have access to this post!"
        )
 
    def test_nonexistent_post_returns_404(self):
        """Test that accessing a non-existent post returns 404"""
        request = self.factory.get('/fake-url')
        request.user = self.author
        
        @user_is_author
        def test_view(request, post_id):
            return "success"
        
        with self.assertRaises(Exception):  # Will raise Http404
            test_view(request, post_id=99999)
 
 
class PostCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        cls.url = reverse('blog:post_create')  # Adjust name as needed
 
    def test_login_required(self):
        """Test that unauthenticated users are redirected to login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
 
    def test_get_request_returns_create_form(self):
        """Test GET request returns the create form"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/create.html')
        self.assertIsInstance(response.context['form'], PostForm)
 
    def test_successful_post_creation(self):
        """Test successful post creation"""
        self.client.login(username='testuser', password='testpass123')
        
        post_data = {
            'title': 'New Post',
            'body': 'This is a test post',
            'status': 'PB',
        }
        
        response = self.client.post(self.url, post_data, follow=True)
        
        # Check post was created
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.title, 'New Post')
        self.assertEqual(post.author, self.user)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Your post has been created!")
        
        # Check redirect
        self.assertRedirects(response, post.get_absolute_url())
 
    @patch('blog.views.Post.published')
    def test_duplicate_post_today_prevents_creation(self, mock_published):
        """Test that duplicate post on same day is prevented"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock that a post with same title exists today
        mock_published.filter.return_value.exists.return_value = True
        
        post_data = {
            'title': 'Duplicate Post',
            'body': 'This content should not be saved',
            'status': 'PB',
        }
        
        response = self.client.post(self.url, post_data)
        
        # Check no post was created
        self.assertEqual(Post.objects.count(), 0)
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0]),
            "A post with the same title was already published today."
        )
        
        # Check form is re-rendered
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/create.html')
 
    def test_invalid_form_does_not_create_post(self):
        """Test that invalid form data doesn't create a post"""
        self.client.login(username='testuser', password='testpass123')
        
        # Submit empty data (form should be invalid)
        response = self.client.post(self.url, {})
        
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/create.html')
        # self.assertTrue(response.context['form'].errors)
 
 
class PostUpdateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Original Title',
            # slug='original-title',
            body='Original content',
            author=cls.author,
            status='PB',
        )
        cls.url = reverse('blog:post_update', kwargs={'post_id': cls.post.id, })
 
    def test_login_required(self):
        """Test that unauthenticated users are redirected"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
 
    def test_non_author_cannot_update(self):
        """Test that non-author cannot access update view"""
        self.client.login(username='other', password='testpass123')
        response = self.client.get(self.url)
        
        # Should redirect to post detail with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.post.get_absolute_url())
 
    def test_get_request_returns_update_form(self):
        """Test GET request returns update form with post data"""
        self.client.login(username='author', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/update.html')
        self.assertEqual(response.context['post'], self.post)
        self.assertEqual(response.context['form'].instance, self.post)
 
    def test_successful_post_update(self):
        """Test successful post update"""
        self.client.login(username='author', password='testpass123')
        
        updated_data = {
            'title': 'Updated Title',
            'body': 'Updated content',
            'status': 'PB',
        }
        
        response = self.client.post(self.url, updated_data, follow=True)
        
        # Check post was updated
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Updated Title')
        self.assertEqual(self.post.body, 'Updated content')
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Your post has been updated!")
        
        # Check redirect
        self.assertRedirects(response, self.post.get_absolute_url())
 
    def test_invalid_update_does_not_change_post(self):
        """Test that invalid update doesn't change the post"""
        self.client.login(username='author', password='testpass123')
        
        original_title = self.post.title
        response = self.client.post(self.url, {})  # Empty data
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, original_title)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/update.html')
        # self.assertTrue(response.context['form'].errors)
 
 
class PostDeleteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Original Title',
            slug='original-title',
            body='Original content',
            author=cls.author,
            status='PB',
        )
        cls.url = reverse('blog:post_delete', kwargs={'post_id': cls.post.id})
 
    def test_login_required(self):
        """Test that unauthenticated users are redirected"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
 
    def test_non_author_cannot_delete(self):
        """Test that non-author cannot access delete view"""
        self.client.login(username='other', password='testpass123')
        response = self.client.get(self.url)
        
        # Should redirect to post detail with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.post.get_absolute_url())
 
    def test_get_request_returns_confirmation_page(self):
        """Test GET request returns confirmation page"""
        self.client.login(username='author', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/confirm_delete.html')
        self.assertEqual(response.context['post'], self.post)
 
    def test_successful_post_deletion(self):
        """Test successful post deletion via POST request"""
        self.client.login(username='author', password='testpass123')
        
        response = self.client.post(self.url, follow=True)
        
        # Check post was deleted
        self.assertEqual(Post.objects.count(), 0)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), "Your post has been deleted!")
        
        # Check redirect to home
        self.assertRedirects(response, '/')
 
    def test_get_request_does_not_delete_post(self):
        """Test that GET request does not delete the post"""
        self.client.login(username='author', password='testpass123')
        
        response = self.client.get(self.url)
        
        # Post should still exist
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
 
 
class IntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
 
    def test_full_post_lifecycle(self):
        """Test complete post lifecycle: create, update, delete"""
        
        # 1. Create a post
        create_url = reverse('blog:post_create')
        post_data = {
            'title': 'Lifecycle Post',
            'body': 'Initial content',
            'status': 'PB',
            'author': self.user
        }
        response = self.client.post(create_url, post_data, follow=True)
        
        post = Post.objects.get(title='Lifecycle Post')
        self.assertEqual(post.author, self.user)
        
        # 2. Update the post
        update_url = reverse('blog:post_update', kwargs={'post_id': post.id})
        updated_data = {
            'title': 'Updated Lifecycle Post',
            'body': 'Updated content',
            # 'slug': 'updated-lifecycle',
            'status': 'PB',
        }
        response = self.client.post(update_url, updated_data, follow=True)
        
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Lifecycle Post')
        
        # 3. Delete the post
        delete_url = reverse('blog:post_delete', kwargs={'post_id': post.id})
        response = self.client.post(delete_url, follow=True)
        
        self.assertEqual(Post.objects.count(), 0)
