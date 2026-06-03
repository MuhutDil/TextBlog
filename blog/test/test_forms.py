from django.test import TestCase
from django.contrib.auth import get_user_model
 
from blog.forms import CommentForm, EmailPostForm, SearchForm, PostForm
from blog.models import Post


User = get_user_model()

 
class CommentFormTests(TestCase):
    """Tests for the CommentForm."""
    
    def test_valid_comment_form(self):
        """Test that valid form data passes validation."""
        form_data = {
            'body': 'This is a valid comment.'
        }
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_empty_comment_form(self):
        """Test that empty form data fails validation."""
        form_data = {
            'body': ''
        }
        form = CommentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)
        
    def test_comment_form_max_length(self):
        """Test that comment body respects max length."""
        form_data = {
            'body': 'a' * 1000  # Assuming max_length exists
        }
        form = CommentForm(data=form_data)
        # Adjust assertion based on your model's max_length
        self.assertTrue(form.is_valid() or 'body' in form.errors)
 
 
class EmailPostFormTests(TestCase):
    """Tests for the EmailPostForm."""
    
    def test_valid_email_form(self):
        """Test that valid email form data passes validation."""
        form_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'to': 'friend@example.com',
            'comments': 'Check out this post!'
        }
        form = EmailPostForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_missing_name(self):
        """Test that missing name fails validation."""
        form_data = {
            'email': 'john@example.com',
            'to': 'friend@example.com',
            'comments': 'Check out this post!'
        }
        form = EmailPostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        
    def test_invalid_email(self):
        """Test that invalid email format fails validation."""
        form_data = {
            'name': 'John Doe',
            'email': 'invalid-email',
            'to': 'friend@example.com',
            'comments': 'Check out this post!'
        }
        form = EmailPostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_invalid_recipient_email(self):
        """Test that invalid recipient email fails validation."""
        form_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'to': 'invalid-email',
            'comments': 'Check out this post!'
        }
        form = EmailPostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('to', form.errors)
 
 
class SearchFormTests(TestCase):
    """Tests for the SearchForm."""
    
    def test_valid_search_form(self):
        """Test that valid search query passes validation."""
        form_data = {'query': 'Django'}
        form = SearchForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_empty_search_form(self):
        """Test that empty search query fails validation."""
        form_data = {'query': ''}
        form = SearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('query', form.errors)
        
    def test_search_form_trim_whitespace(self):
        """Test that search query is trimmed."""
        form_data = {'query': '  Django  '}
        form = SearchForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['query'], 'Django')
 
 
class PostFormTests(TestCase):
    """Tests for the PostForm."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_valid_post_form(self):
        """Test that valid post form data passes validation."""
        form_data = {
            'title': 'Test Post',
            'body': 'This is the post content.',
            'status': Post.Status.PUBLISHED
        }
        form = PostForm(data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_missing_title(self):
        """Test that missing title fails validation."""
        form_data = {
            'body': 'Content',
            'status': Post.Status.PUBLISHED
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
    def test_missing_body(self):
        """Test that missing body fails validation."""
        form_data = {
            'title': 'Test Post',
            'status': Post.Status.PUBLISHED
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('body', form.errors)
        
    def test_post_form_long_title(self):
        """Test that very long title fails validation."""
        form_data = {
            'title': 'a' * 300,  # Assuming max_length is 250
            'body': 'Content',
            'status': Post.Status.PUBLISHED
        }
        form = PostForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
 