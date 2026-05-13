from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from .models import Post
from .views import post_list
 
User = get_user_model()
 
class PostListViewTest(TestCase):
 
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create published posts
        Post.objects.create(
            title='Published Post 1',
            slug='published-post-1',
            author=self.user,
            body='Content for published post 1.',
            status=Post.Status.PUBLISHED,
        )
        Post.objects.create(
            title='Published Post 2',
            slug='published-post-2',
            author=self.user,
            body='Content for published post 2.',
            status=Post.Status.PUBLISHED,
        )
        # Create a draft post (should NOT appear in results)
        Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            author=self.user,
            body='Content for draft post.',
            status=Post.Status.DRAFT,
        )
    
    def tearDown(self):
        Post.objects.all().delete()
        User.objects.all().delete()
 
    def test_view_returns_200(self):
        """View should return a 200 OK response."""
        request = self.factory.get('/')
        response = post_list(request)
        self.assertEqual(response.status_code, 200)
 
    def test_view_uses_correct_template(self):
        """View should render the correct template."""
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'blog/post/list.html')
 
    def test_context_contains_posts(self):
        """Context should contain a 'posts' key."""
        response = self.client.get('/')
        self.assertIn('posts', response.context)
 
    def test_only_published_posts_returned(self):
        """Only published posts should appear — drafts must be excluded."""
        response = self.client.get('/')
        posts = response.context['posts']
        self.assertEqual(posts.count(), 2)
        for post in posts:
            self.assertEqual(post.status, Post.Status.PUBLISHED)
 
    def test_draft_post_not_in_context(self):
        """The draft post should not appear in the context."""
        response = self.client.get('/')
        posts = response.context['posts']
        titles = [p.title for p in posts]
        self.assertNotIn('Draft Post', titles)
 
