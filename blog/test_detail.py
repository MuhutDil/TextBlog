from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import Http404
from .models import Post
from .views import post_detail

User = get_user_model()
 
 
class PostDetailViewTest(TestCase):
 
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create a published post
        self.published_post = Post.objects.create(
            title='Published Post',
            slug='published-post',
            author=self.user,
            body='Content for published post.',
            status=Post.Status.PUBLISHED,
        )
        # Create a draft post
        self.draft_post = Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            author=self.user,
            body='Content for draft post.',
            status=Post.Status.DRAFT,
        )
 
    def test_published_post_returns_200(self):
        """A valid published post should return 200 OK."""
        request = self.factory.get('/')
        response = post_detail(request, id=self.published_post.id)
        self.assertEqual(response.status_code, 200)
 
    def test_draft_post_returns_404(self):
        """A draft post should return 404 — not publicly accessible."""
        request = self.factory.get('/')
        with self.assertRaises(Http404):
            post_detail(request, id=self.draft_post.id)
 
    def test_nonexistent_post_returns_404(self):
        """A non-existent post ID should return 404."""
        request = self.factory.get('/')
        with self.assertRaises(Http404):
            post_detail(request, id=99999)
 
    def test_correct_template_used(self):
        """View should render the correct template."""
        url = reverse('blog:post_detail', args=[self.published_post.id])
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'blog/post/detail.html')
 
    def test_context_contains_post(self):
        """Context should contain the correct 'post' object."""
        url = reverse('blog:post_detail', args=[self.published_post.id])
        response = self.client.get(url)
        self.assertIn('post', response.context)
        self.assertEqual(response.context['post'], self.published_post)
 
    def test_context_post_is_published(self):
        """The post returned in context must have PUBLISHED status."""
        url = reverse('blog:post_detail', args=[self.published_post.id])
        response = self.client.get(url)
        post = response.context['post']
        self.assertEqual(post.status, Post.Status.PUBLISHED)
 
    def test_context_post_has_correct_fields(self):
        """The post in context should match the expected title and body."""
        url = reverse('blog:post_detail', args=[self.published_post.id])
        response = self.client.get(url)
        post = response.context['post']
        self.assertEqual(post.title, 'Published Post')
        self.assertEqual(post.body, 'Content for published post.')
 
    def tearDown(self):
        Post.objects.all().delete()
        User.objects.all().delete()