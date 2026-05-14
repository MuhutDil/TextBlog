from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import Http404
from blog.models import Post
from blog.views import post_list, post_detail
 
User = get_user_model()

class BaseViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create published posts
        self.published_post = Post.objects.create(
            title='Published Post 1',
            slug='published-post-1',
            author=self.user,
            body='Content for published post 1.',
            status=Post.Status.PUBLISHED,
        )
        self.another_published_post = Post.objects.create(
            title='Published Post 2',
            slug='published-post-2',
            author=self.user,
            body='Content for published post 2.',
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
    
    def tearDown(self):
        Post.objects.all().delete()
        User.objects.all().delete()

class PostListViewTest(BaseViewTest):
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
 

class PostDetailViewTest(BaseViewTest):
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
        self.assertEqual(post.title, 'Published Post 1')
        self.assertEqual(post.body, 'Content for published post 1.')

