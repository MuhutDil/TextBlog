from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
 
from blog.models import Post, Comment, Tag
from blog.forms import CommentForm, EmailPostForm, SearchForm, PostForm

User = get_user_model()
 
class PostModelTests(TestCase):
    """Tests for the Post model and its functionality."""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
    def test_create_draft_post(self):
        """Test creating a draft post."""
        post = Post.objects.create(
            title='Draft Post',
            body='This is a draft post content.',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        self.assertEqual(post.title, 'Draft Post')
        self.assertEqual(post.slug, 'draft-post')
        self.assertEqual(post.status, Post.Status.DRAFT)
        self.assertIsNone(post.publish)
        self.assertEqual(str(post), 'Draft Post')
        
    def test_create_published_post(self):
        """Test creating a published post."""
        post = Post.objects.create(
            title='Published Post',
            body='This is published content.',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        self.assertEqual(post.status, Post.Status.PUBLISHED)
        self.assertIsNotNone(post.publish)
        self.assertEqual(post.slug, 'published-post')
        
    def test_duplicate_published_post_same_day(self):
        """Test that duplicate published posts on same day raise exception."""
        Post.objects.create(
            title='First Post',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        with self.assertRaises(Exception) as context:
            Post.objects.create(
                title='First Post',
                body='Different content',
                author=self.user,
                status=Post.Status.PUBLISHED
            )
        self.assertIn('already published today', str(context.exception))
        
    def test_duplicate_draft_post(self):
        """Test that duplicate draft posts by same author raise exception."""
        Post.objects.create(
            title='Draft Post',
            body='Content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        with self.assertRaises(Exception) as context:
            Post.objects.create(
                title='Draft Post',
                body='Different content',
                author=self.user,
                status=Post.Status.DRAFT
            )
        self.assertIn('already have a draft', str(context.exception))
        
    def test_published_manager(self):
        """Test that published manager only returns published posts."""
        Post.objects.create(
            title='Published 1',
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
        Post.objects.create(
            title='Published 2',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        published_posts = Post.published.all()
        self.assertEqual(published_posts.count(), 2)
        self.assertTrue(all(p.status == Post.Status.PUBLISHED for p in published_posts))
        
    def test_get_absolute_url_published(self):
        """Test get_absolute_url for published post."""
        post = Post.objects.create(
            title='Test Post',
            body='Content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        
        url = post.get_absolute_url()
        expected_url = reverse(
            'blog:post_detail',
            args=[post.publish.year, post.publish.month, post.publish.day, post.slug]
        )
        self.assertEqual(url, expected_url)
        
    def test_get_absolute_url_draft(self):
        """Test get_absolute_url for draft post."""
        post = Post.objects.create(
            title='Draft Post',
            body='Content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        url = post.get_absolute_url()
        expected_url = reverse('blog:draft_detail', args=[post.slug])
        self.assertEqual(url, expected_url)
 
 
class CommentModelTests(TestCase):
    """Tests for the Comment model."""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Test Post',
            body='Content',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        
    def test_create_comment(self):
        """Test creating a comment on a post."""
        comment = Comment.objects.create(
            post=self.post,
            commented_by=self.user,
            body='This is a great post!'
        )
        
        self.assertEqual(comment.body, 'This is a great post!')
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.commented_by, self.user)
        self.assertTrue(comment.active)
        self.assertEqual(str(comment), f'Comment by {self.user} on {self.post}')
        
    def test_comment_ordering(self):
        """Test that comments are ordered by creation date."""
        comment1 = Comment.objects.create(
            post=self.post,
            commented_by=self.user,
            body='First comment'
        )
        comment2 = Comment.objects.create(
            post=self.post,
            commented_by=self.user,
            body='Second comment'
        )
        
        comments = Comment.objects.all()
        self.assertEqual(comments[0], comment1)
        self.assertEqual(comments[1], comment2)
 
 
class PostListViewTests(TestCase):
    """Tests for the post list view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.url = reverse('blog:post_list')
        
        # Create multiple published posts
        for i in range(5):
            Post.objects.create(
                title=f'Post {i}',
                body=f'Content {i}',
                author=cls.user,
                status=Post.Status.PUBLISHED
            )
            
    def test_post_list_view_status_code(self):
        """Test that post list view returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
    def test_post_list_view_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'blog/list.html')
        
    def test_post_list_pagination(self):
        """Test that posts are paginated correctly."""
        response = self.client.get(self.url)
        self.assertIn('posts', response.context)
        self.assertEqual(len(response.context['posts']), 3)  # POSTS_ON_PAGE = 3
        
    def test_post_list_pagination_page2(self):
        """Test second page of pagination."""
        response = self.client.get(self.url, {'page': 2})
        self.assertEqual(len(response.context['posts']), 2)
        
    def test_post_list_only_published(self):
        """Test that only published posts appear in list."""
        Post.objects.create(
            title='Draft Post',
            body='Draft content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        response = self.client.get(self.url)
        posts = response.context['posts']
        self.assertNotIn('Draft Post', [p.title for p in posts])
        self.assertEqual(Post.published.count(), 5)  # Only the 5 published posts
        
    def test_post_list_filter_by_tag(self):
        """Test filtering posts by tag."""
        post = Post.published.first()
        tag = Tag.objects.create(name='python')
        post.tags.add(tag)

        response = self.client.get(reverse('blog:post_list_by_tag', args=[tag.slug]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['tag'], tag)
        
    def test_post_list_invalid_page(self):
        """Test that invalid page number returns first page."""
        response = self.client.get(self.url, {'page': 'abc'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].number, 1)
        
    def test_post_list_out_of_range_page(self):
        """Test that out of range page returns last page."""
        response = self.client.get(self.url, {'page': 999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['posts'].number, 2)  # 5 posts, 3 per page = 2 pages
 
 
class PostDetailViewTests(TestCase):
    """Tests for the post detail view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Test Post',
            body='Test content',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        cls.url = cls.post.get_absolute_url()
        
    def test_post_detail_view_status_code(self):
        """Test that post detail view returns 200."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
    def test_post_detail_view_template(self):
        """Test that correct template is used."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'blog/detail.html')
        
    def test_post_detail_context(self):
        """Test that post detail view contains correct context."""
        response = self.client.get(self.url)
        self.assertEqual(response.context['post'], self.post)
        self.assertIn('comments', response.context)
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], CommentForm)
        
    def test_post_detail_shows_comments(self):
        """Test that active comments are displayed."""
        comment = Comment.objects.create(
            post=self.post,
            commented_by=self.user,
            body='Great post!',
            active=True
        )
        
        response = self.client.get(self.url)
        self.assertIn(comment, response.context['comments'])
        
    def test_post_detail_hides_inactive_comments(self):
        """Test that inactive comments are not displayed."""
        comment = Comment.objects.create(
            post=self.post,
            commented_by=self.user,
            body='Spam comment',
            active=False
        )
        
        response = self.client.get(self.url)
        self.assertNotIn(comment, response.context['comments'])
        
    def test_post_detail_similar_posts(self):
        """Test that similar posts are shown based on tags."""
        post2 = Post.objects.create(
            title='Similar Post',
            body='Similar content',
            author=self.user,
            status=Post.Status.PUBLISHED
        )
        tag = Tag.objects.create(
            name='python'
        )
        
        self.post.tags.add(tag)
        post2.tags.add(tag)
        
        response = self.client.get(self.url)
        self.assertIn('similar_posts', response.context)
        self.assertIn(post2, response.context['similar_posts'])
        
    def test_draft_post_not_accessible_by_public(self):
        """Test that draft posts are not accessible by public users."""
        draft = Post.objects.create(
            title='Draft Post',
            body='Draft content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
        
    def test_draft_post_accessible_by_author(self):
        """Test that draft posts are accessible by the author."""
        self.client.login(username='testuser', password='testpass123')
        draft = Post.objects.create(
            title='Draft Post',
            body='Draft content',
            author=self.user,
            status=Post.Status.DRAFT
        )
        
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)
 
 
class PostCreateViewTests(TestCase):
    """Tests for the post creation view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        cls.url = reverse('blog:post_create')
        
    def test_create_view_requires_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))
        
    def test_create_view_get_request(self):
        """Test GET request to create view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/create.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], PostForm)
        
    def test_create_post_success(self):
        """Test successful post creation."""
        self.client.login(username='testuser', password='testpass123')
        post_data = {
            'title': 'New Post',
            'body': 'This is a new post.',
            'status': Post.Status.PUBLISHED,
        }
        
        response = self.client.post(self.url, post_data)
        
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.title, 'New Post')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.status, Post.Status.PUBLISHED)
        
    def test_create_draft_post_success(self):
        """Test successful draft post creation."""
        self.client.login(username='testuser', password='testpass123')
        post_data = {
            'title': 'Draft Post',
            'body': 'This is a draft.',
            'status': Post.Status.DRAFT
        }
        
        response = self.client.post(self.url, post_data)
        
        post = Post.objects.first()
        self.assertEqual(post.status, Post.Status.DRAFT)
        self.assertIsNone(post.publish)
        
    def test_create_post_invalid_data(self):
        """Test creating post with invalid data."""
        self.client.login(username='testuser', password='testpass123')
        post_data = {
            'title': '',  # Empty title
            'body': 'Content'
        }
        
        response = self.client.post(self.url, post_data)
        
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
 
 
class PostUpdateViewTests(TestCase):
    """Tests for the post update view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@email.com',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            username='otheruser',
            email='otheruser@email.com',
            password='otherpass123'
        )
        cls.post = Post.objects.create(
            title='Original Title',
            body='Original content',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        cls.url = reverse('blog:post_update', args=[cls.post.id])
        
    def test_update_view_requires_author(self):
        """Test that only author can update post."""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(self.url)
        
        # Should redirect to post detail with error message
        self.assertEqual(response.status_code, 302)
        
    def test_update_view_get_request(self):
        """Test GET request to update view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/update.html')
        self.assertEqual(response.context['post'], self.post)
        
    def test_update_post_success(self):
        """Test successful post update."""
        self.client.login(username='testuser', password='testpass123')
        update_data = {
            'title': 'Updated Title',
            'body': 'Updated content',
            'status': Post.Status.PUBLISHED
        }
        
        response = self.client.post(self.url, update_data)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, 'Updated Title')
        self.assertEqual(self.post.body, 'Updated content')
        
    def test_update_post_to_draft(self):
        """Test updating published post to draft."""
        self.client.login(username='testuser', password='testpass123')
        update_data = {
            'title': 'Now Draft',
            'body': 'Content',
            'status': Post.Status.DRAFT
        }
        
        response = self.client.post(self.url, update_data)
        
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, Post.Status.DRAFT)
        self.assertIsNone(self.post.publish)
 
 
class PostDeleteViewTests(TestCase):
    """Tests for the post delete view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@email.com',
            password='testpass123'
        )
        cls.other_user = User.objects.create_user(
            username='otheruser',
            email='otheruser@email.com',
            password='otherpass123'
        )
        cls.post = Post.objects.create(
            title='To Delete',
            body='Content',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        cls.url = reverse('blog:post_delete', args=[cls.post.id])
        
    def test_delete_view_requires_author(self):
        """Test that only author can delete post."""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        
    def test_delete_confirmation_page(self):
        """Test that delete confirmation page is shown."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/confirm_delete.html')
        self.assertEqual(response.context['post'], self.post)
        
    def test_delete_post_success(self):
        """Test successful post deletion."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url)
        
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(response.status_code, 302)  # Redirect after deletion
 
 
class PostShareViewTests(TestCase):
    """Tests for the post sharing via email view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@email.com',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Shareable Post',
            body='Content to share',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        cls.url = reverse('blog:post_share', args=[cls.post.id])
        
    def test_share_view_get_request(self):
        """Test GET request to share view."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/share.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], EmailPostForm)
        
    def test_share_post_success(self):
        """Test successfully sharing a post via email."""
        share_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'to': 'friend@example.com',
            'comments': 'Check this out!'
        }
        
        response = self.client.post(self.url, share_data)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('recommends you read Shareable Post', email.subject)
        self.assertEqual(email.to, ['friend@example.com'])
        
        # Check context
        self.assertTrue(response.context['sent'])
        
    def test_share_post_invalid_form(self):
        """Test sharing with invalid form data."""
        share_data = {
            'name': '',  # Empty name
            'email': 'invalid-email',
            'to': 'friend@example.com',
            'comments': 'Check this out!'
        }
        
        response = self.client.post(self.url, share_data)
        
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(response.context['sent'])
        self.assertTrue(response.context['form'].errors)
 
 
class PostCommentViewTests(TestCase):
    """Tests for the comment submission view."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@email.com',
            password='testpass123'
        )
        cls.post = Post.objects.create(
            title='Test Post',
            body='Content',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        cls.url = reverse('blog:post_comment', args=[cls.post.id])
        
    def test_comment_view_requires_post(self):
        """Test that comment view only accepts POST requests."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
        
    def test_add_comment_success(self):
        """Test successfully adding a comment."""
        self.client.login(username='testuser', password='testpass123')
        comment_data = {
            'body': 'This is a great post!'
        }
        
        response = self.client.post(self.url, comment_data)
        
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.body, 'This is a great post!')
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.commented_by, self.user)
        self.assertTrue(comment.active)
        
    def test_add_comment_without_login(self):
        """Test that login is required to comment."""
        comment_data = {
            'body': 'This is a comment'
        }

        response = self.client.post(self.url, comment_data)
        self.assertTrue(response.url.startswith('/login/'))

        
    def test_add_comment_invalid_data(self):
        """Test adding comment with invalid data."""
        self.client.login(username='testuser', password='testpass123')
        comment_data = {
            'body': ''  # Empty comment
        }
        
        response = self.client.post(self.url, comment_data)
        
        self.assertEqual(Comment.objects.count(), 0)
 
 
class PostSearchViewTests(TestCase):
    """Tests for the search functionality."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            email='testuser@email.com',
            password='testpass123'
        )
        cls.url = reverse('blog:post_search')
        
        # Create test posts
        Post.objects.create(
            title='Django Tutorial',
            body='Learn Django framework',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        Post.objects.create(
            title='Python Tips',
            body='Python programming tips',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        Post.objects.create(
            title='JavaScript Guide',
            body='JS for beginners',
            author=cls.user,
            status=Post.Status.PUBLISHED
        )
        
    def test_search_view_get_request(self):
        """Test GET request to search view."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'blog/search.html')
        self.assertIsInstance(response.context['form'], SearchForm)
        self.assertIsNone(response.context['query'])
        self.assertEqual(response.context['results'], [])
        
    def test_search_with_query(self):
        """Test searching with a query string."""
        response = self.client.get(self.url, {'query': 'Django'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['query'], 'Django')
        self.assertGreater(len(response.context['results']), 0)
        
    def test_search_no_results(self):
        """Test search that returns no results."""
        response = self.client.get(self.url, {'query': 'Ruby'})
        
        self.assertEqual(len(response.context['results']), 0)
        
    def test_search_empty_query(self):
        """Test search with empty query."""
        response = self.client.get(self.url, {'query': ''})
        
        # Form should be invalid, results should be empty
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(len(response.context['results']), 0)
        
    def test_search_trigram_similarity(self):
        """Test that trigram similarity finds partial matches."""
        response = self.client.get(self.url, {'query': 'Djan'})
        
        self.assertGreater(len(response.context['results']), 0)
        self.assertTrue(any('Django' in post.title for post in response.context['results']))
 
 
class UserIsAuthorDecoratorTests(TestCase):
    """Tests for the custom user_is_author decorator."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.author = User.objects.create_user(
            username='author',
            email='testuser@email.com',
            password='authorpass'
        )
        cls.other_user = User.objects.create_user(
            username='other',
            email='other@email.com',
            password='otherpass'
        )
        cls.post = Post.objects.create(
            title='Author Post',
            body='Content',
            author=cls.author,
            status=Post.Status.PUBLISHED
        )
        
    def test_author_can_access(self):
        """Test that author can access protected views."""
        self.client.login(username='author', password='authorpass')
        response = self.client.get(reverse('blog:post_update', args=[self.post.id]))
        
        self.assertEqual(response.status_code, 200)
        
    def test_non_author_redirected(self):
        """Test that non-author is redirected with error message."""
        self.client.login(username='other', password='otherpass')
        response = self.client.get(reverse('blog:post_update', args=[self.post.id]))
        
        self.assertEqual(response.status_code, 302)  # Redirect
        # Check that redirect goes to post detail
        self.assertTrue(self.post.get_absolute_url() in response.url)
        
    def test_unauthenticated_redirected_to_login(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(reverse('blog:post_update', args=[self.post.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.post.get_absolute_url() in response.url)
 
 
class PaginationTests(TestCase):
    """Tests for pagination functionality."""
    
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create 10 published posts
        for i in range(10):
            Post.objects.create(
                title=f'Post {i}',
                body=f'Content {i}',
                author=cls.user,
                status=Post.Status.PUBLISHED
            )
            
    def test_first_page_has_limited_posts(self):
        """Test that first page shows limited number of posts."""
        response = self.client.get(reverse('blog:post_list'))
        posts = response.context['posts']
        
        self.assertEqual(len(posts), 3)  # POSTS_ON_PAGE = 3
        
    def test_second_page_has_posts(self):
        """Test that second page shows next set of posts."""
        response = self.client.get(reverse('blog:post_list'), {'page': 2})
        posts = response.context['posts']
        
        self.assertEqual(len(posts), 3)
        
    def test_last_page_has_remaining_posts(self):
        """Test that last page shows remaining posts."""
        response = self.client.get(reverse('blog:post_list'), {'page': 4})
        posts = response.context['posts']
        
        self.assertEqual(len(posts), 1)  # 10 posts, 3 per page = 4th page has 1 post
 