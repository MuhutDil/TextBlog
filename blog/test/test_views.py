from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import Http404
from blog.models import Post
from blog.views import post_list, post_detail
import math

from blog.views import POSTS_ON_PAGE
 
User = get_user_model()

class BaseViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create published posts
        cls.published_post = Post.objects.create(
            title='Published Post 1',
            slug='published-post-1',
            author=cls.user,
            body='Content for published post 1.',
            status=Post.Status.PUBLISHED,
        )
        cls.another_published_post = Post.objects.create(
            title='Published Post 2',
            slug='published-post-2',
            author=cls.user,
            body='Content for published post 2.',
            status=Post.Status.PUBLISHED,
        )
        # Create a draft post
        cls.draft_post = Post.objects.create(
            title='Draft Post',
            slug='draft-post',
            author=cls.user,
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
        self.assertTemplateUsed(response, 'blog/list.html')
 
    def test_context_contains_posts(self):
        """Context should contain a 'posts' key."""
        response = self.client.get('/')
        self.assertIn('posts', response.context)
 
    def test_only_published_posts_returned(self):
        """Only published posts should appear — drafts must be excluded."""
        response = self.client.get('/')
        posts = response.context['posts']
        self.assertEqual(len(posts), 2)
        for post in posts:
            self.assertEqual(post.status, Post.Status.PUBLISHED)
 
    def test_draft_post_not_in_context(self):
        """The draft post should not appear in the context."""
        response = self.client.get('/')
        posts = response.context['posts']
        titles = [p.title for p in posts]
        self.assertNotIn('Draft Post', titles)
 

class PostDetailViewTest(BaseViewTest):
    def _published_post_data(self):
        return {
            'year': self.published_post.publish.year,
            'month': self.published_post.publish.month,
            'day': self.published_post.publish.day,
            'post': self.published_post.slug,
        }

    def _draft_post_data(self):
        return {
            'year': self.draft_post.publish.year,
            'month': self.draft_post.publish.month,
            'day': self.draft_post.publish.day,
            'post': self.draft_post.slug,
        }

    def test_published_post_returns_200(self):
        """A valid published post should return 200 OK."""
        request = self.factory.get('/')
        response = post_detail(request, **self._published_post_data())
        self.assertEqual(response.status_code, 200)
 
    def test_draft_post_returns_200(self):
        """A draft post should return 200 OK."""
        request = self.factory.get('/')
        response = post_detail(request, **self._published_post_data())
        self.assertEqual(response.status_code, 200)
 
    def test_nonexistent_post_returns_404(self):
        """A non-existent post ID should return 404."""
        request = self.factory.get('/')
        with self.assertRaises(Http404):
            post_detail(
                request, 
                year=2000, 
                month=1, 
                day=1, 
                post='dont-exist')
 
    def test_correct_template_used(self):
        """View should render the correct template."""
        url = reverse('blog:post_detail', kwargs=self._published_post_data())
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'blog/detail.html')
 
    def test_context_contains_post(self):
        """Context should contain the correct 'post' object."""
        url = reverse('blog:post_detail', kwargs=self._published_post_data())
        response = self.client.get(url)
        self.assertIn('post', response.context)
        self.assertEqual(response.context['post'], self.published_post)
 
    def test_context_post_is_published(self):
        """The post returned in context must have PUBLISHED status."""
        url = reverse('blog:post_detail', kwargs=self._published_post_data())
        response = self.client.get(url)
        post = response.context['post']
        self.assertEqual(post.status, Post.Status.PUBLISHED)
 
    def test_context_post_has_correct_fields(self):
        """The post in context should match the expected title and body."""
        url = reverse('blog:post_detail', kwargs=self._published_post_data())
        response = self.client.get(url)
        post = response.context['post']
        self.assertEqual(post.title, 'Published Post 1')
        self.assertEqual(post.body, 'Content for published post 1.')


class PostListViewPaginationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # Create 25 blog posts
        cls.last_page = math.ceil(25 / POSTS_ON_PAGE)
        for i in range(25):
            Post.objects.create(
                title=f'Published Post {i}',
                slug=f'published-post-{i}',
                author=cls.user,
                body=f'Content for published post {i}.',
                status=Post.Status.PUBLISHED,
            )
    
    def test_first_page_returns_correct_amount_posts(self):
        response = self.client.get('/?page=1')
        self.assertEqual(len(response.context['posts']), POSTS_ON_PAGE)
        self.assertEqual(response.context['posts'][0].title, 'Published Post 24')
        
    def test_page_out_of_range_returns_last_page(self):
        response = self.client.get('/?page=100')
        self.assertEqual(response.context['page'].number, self.last_page)
    
    def test_invalid_page_returns_first_page(self):
        response = self.client.get('/?page=abc')
        self.assertEqual(response.context['page'].number, 1)
    