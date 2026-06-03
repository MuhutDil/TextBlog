from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
 
from blog.models import Post


User = get_user_model()
 
class PostManagerTests(TestCase):
    """Tests for custom Post managers."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_published_manager_only_returns_published(self):
        """Test that PublishedManager only returns published posts."""
        Post.objects.create(
            title='Published 1',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        Post.objects.create(
            title='Published 2',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        Post.objects.create(
            title='Draft 1',
            body='Content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        published_posts = Post.published.all()
        self.assertEqual(published_posts.count(), 2)
        
        all_posts = Post.objects.all()
        self.assertEqual(all_posts.count(), 3)
        
    def test_published_manager_chainable(self):
        """Test that PublishedManager can be chained with other queryset methods."""
        Post.objects.create(
            title='First Post',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        Post.objects.create(
            title='Second Post',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        # Test filtering on published queryset
        result = Post.published.filter(title='First Post')
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().title, 'First Post')
 
 
class PostSaveMethodTests(TestCase):
    """Tests for the Post model's save method."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_slug_auto_generation(self):
        """Test that slug is automatically generated from title."""
        post = Post.objects.create(
            title='This Is A Test Post!',
            body='Content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        self.assertEqual(post.slug, 'this-is-a-test-post')
        
    def test_publish_date_set_on_publication(self):
        """Test that publish date is set when post is published."""
        before_create = timezone.now()
        post = Post.objects.create(
            title='Test Post',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        after_create = timezone.now()
        
        self.assertIsNotNone(post.publish)
        self.assertTrue(before_create <= post.publish <= after_create)
        
    def test_publish_date_none_for_draft(self):
        """Test that publish date is None for draft posts."""
        post = Post.objects.create(
            title='Draft Post',
            body='Content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        self.assertIsNone(post.publish)
        
    def test_duplicate_published_post_different_days(self):
        """Test that duplicate titles on different days are allowed."""
        post1 = Post.objects.create(
            title='Same Title',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        # Mock the publish date to be tomorrow
        post1.publish = timezone
 