from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from functools import wraps
import redis
from django.conf import settings

from .forms import CommentForm, EmailPostForm, SearchForm, PostForm, TagForm
from .models import Post, Tag, PostAlreadyExist, DraftAlreadyExist, TagAlreadyExist


User = get_user_model()


POSTS_ON_PAGE = 3
COUNT_SIMILAR_POST = 4

r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
)


def user_is_author(view_func):
    """
    Decorator to restrict view access to the author of a blog post.
    
    This decorator retrieves a Post object by its ID from the URL kwargs,
    checks if the currently logged-in user is the author of that post,
    and either allows access or redirects with an error message.
    
    Args:
        view_func: The view function to be decorated.
        
    Returns:
        function: The wrapped view function that includes authorization logic.
        
    Behavior:
        - If user is author: passes the post object as a keyword argument and calls the view
        - If user is not author: displays error message and redirects to the post detail page
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        post = get_object_or_404(Post, id=kwargs['post_id'])
        
        # Check if the logged-in user is the author
        if post.author == request.user:
            kwargs['post'] = post
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You don't have access to this post!")
            return redirect(post.get_absolute_url())
            
    return _wrapped_view


def paginate(request, object_list, per_page=POSTS_ON_PAGE):
    paginator = Paginator(object_list, per_page)
    page_number = request.GET.get('page', 1)
    try:
        objects = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer get the first page
        objects = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range get last page of results
        objects = paginator.page(paginator.num_pages)
    return objects


@login_required
def post_create(request):
    """
    Create a new blog post.
    
    This view handles both GET and POST requests for creating a new post.
    For GET requests, it displays an empty form. For POST requests, it validates
    the form data, saves the post with the current user as author, and handles
    duplicate post/draft exceptions.
    
    Args:
        request: HTTP request object.
        
    Returns:
        HttpResponse: Renders the post creation form on GET or validation errors,
                     or redirects to the post detail page on successful creation.
    """
    form = PostForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            messages.success(request, "Your post has been created!")
            return redirect(post.get_absolute_url())
        except (PostAlreadyExist, DraftAlreadyExist) as e:
            messages.error(request, str(e))
    
    return render(
        request,
        'blog/create.html',
        {'form': form},
    )

def post_list(request, tag_slug=None):
    """
    Display a paginated list of published blog posts, optionally filtered by tag.
    
    Args:
        request: HTTP request object.
        tag_slug: Optional slug string for filtering posts by a specific tag.
        
    Returns:
        HttpResponse: Renders the blog list template with paginated posts and optional tag.
    """
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    posts = paginate(request, post_list)
    return render(
        request,
        'blog/list.html',
        {
            'posts': posts,
            'tag': tag,
        }
    )


def post_detail(request, year, month, day, post):
    """
    Display the detailed view of a single published blog post.
    
    This view retrieves a published post based on its publication date and slug,
    displays its active comments, and shows a list of similar posts based on tags.
    
    Args:
        request: HTTP request object.
        year: Publication year of the post.
        month: Publication month of the post.
        day: Publication day of the post.
        post: Slug of the post.
        
    Returns:
        HttpResponse: Renders the post detail template with post, comments,
                     comment form, and similar posts.
    """
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )
    total_views = r.incr(f'post:{post.id}:views')
    r.zincrby("posts_ranking", 1, post.id)
    # List of active comments for this post
    comments = post.comments.filter(active=True)
    # Form for users to comment
    form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(
        tags__in=post_tags_ids
    ).exclude(id=post.id)
    similar_posts = similar_posts.annotate(
        same_tags=Count('tags')
    ).order_by('-same_tags', '-publish')[:COUNT_SIMILAR_POST]

    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
            'comments': comments,
            'form': form,
            'similar_posts': similar_posts,
            'total_views': total_views,
        },
    )



@user_is_author
def post_update(request, post_id, post=None):
    """
    Update an existing blog post.
    
    This view is restricted to the post author via the @user_is_author decorator.
    It displays a form pre-populated with the post's current data and handles
    form submission for updating the post.
    
    Args:
        request: HTTP request object.
        post_id: ID of the post to be updated.
        post: Post object injected by the user_is_author decorator.
        
    Returns:
        HttpResponse: Renders the update form on GET, redirects to post detail
                     on successful update, or redisplays form with errors.
    """
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
            messages.success(request, "Your post has been updated!")
            return redirect(post.get_absolute_url())
        except (PostAlreadyExist, DraftAlreadyExist) as e:
            messages.error(request, str(e))
    return render(
        request,
        'blog/update.html',
        {
            'post': post,
            'form': form,
        },
    )

@user_is_author
def post_delete(request, post_id, post=None):
    """
    Delete an existing blog post.
    
    This view is restricted to the post author via the @user_is_author decorator.
    On GET request, it displays a confirmation page. On POST request, it deletes
    the post and redirects to the homepage.
    
    Args:
        request: HTTP request object.
        post_id: ID of the post to be deleted.
        post: Post object injected by the user_is_author decorator.
        
    Returns:
        HttpResponse: Renders confirmation template on GET, redirects to homepage
                     on successful deletion.
    """
    if request.method == "POST":
        post.delete()
        messages.success(request, "Your post has been deleted!")
        return redirect('/')
    return render(request, 'blog/confirm_delete.html', {'post': post})


@login_required
def draft_detail(request, post):
    """
    Display a draft post for the author.
    
    This view allows the author to view their draft posts before publishing.
    Only shows drafts belonging to the currently logged-in user.
    
    Args:
        request: HTTP request object.
        post: Slug of the draft post.
        
    Returns:
        HttpResponse: Renders the post detail template for the draft post.
    """
    post = get_object_or_404(
        Post,
        slug=post,
        status=Post.Status.DRAFT,
        author=request.user,
    )
    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
        },
    )


def post_share(request, post_id):
    """
    Handle email sharing of a blog post.
    
    This view displays a form for users to share a post via email.
    When the form is submitted, it sends an email with the post link
    to the specified recipient.
    
    Args:
        request: HTTP request object.
        post_id: ID of the post to be shared.
        
    Returns:
        HttpResponse: Renders the share template with form and success status.
    """
    # Retrieve post by id
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(
                post.get_absolute_url()
            )
            subject = (
                f"{cd['name']} ({cd['email']}) "
                f"recommends you read {post.title}"
            )
            message = (
                f"Read {post.title} at {post_url}\n\n"
                f"{cd['name']}'s comments: {cd['comments']}"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd['to']],
            )
            sent = True

    else:
        form = EmailPostForm()
    return render(
        request,
        'blog/share.html',
        {
            'post': post,
            'form': form,
            'sent': sent
        },
    )

@require_POST
@login_required
def post_comment(request, post_id):
    """
    Handle comment submission on a blog post.
    
    This view processes POST requests only. It validates the comment form,
    associates the comment with the current user and post, and saves it to
    the database.
    
    Args:
        request: HTTP request object (must be POST).
        post_id: ID of the post being commented on.
        
    Returns:
        HttpResponse: Renders the comment template with the submitted comment.
    """
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    comment = None
    # A comment was posted
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Create a Comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Assign the user to the comment
        comment.commented_by = request.user
        # Save the comment to the database
        comment.save()
        messages.success(request, "Your comment has been published!")
    return redirect(post.get_absolute_url())


def post_search(request):
    """
    Search for blog posts using trigram similarity on titles.
    
    This view uses PostgreSQL's trigram similarity to find posts with titles
    similar to the search query. Results are filtered to show only those with
    a similarity score above 0.1, ordered by highest similarity first.
    
    Args:
        request: HTTP request object containing optional 'query' parameter.
        
    Returns:
        HttpResponse: Renders the search template with form, query, and results.
    """
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = (
                Post.published.annotate(
                    similarity=TrigramSimilarity('title', query),
                )
                .filter(similarity__gt=0.1)
                .order_by('-similarity')
            )
            results = paginate(request, results)

    return render(
        request,
        'blog/search.html',
        {
            'form': form,
            'query': query,
            'results': results
        },
    )

def post_ranking_view(request):
    post_ranking = r.zrange(
        'posts_ranking', 0, -1, desc=True
    )[:10]
    post_ranking_ids = [int(id) for id in post_ranking]
    most_viewed = list(
        Post.published.filter(
            id__in=post_ranking_ids
        )
    )
    most_viewed.sort(key=lambda x: post_ranking_ids.index(x.id))
    posts = paginate(request, most_viewed)
    return render(
        request,
        'blog/ranking.html',
        {
            'posts': posts,
            'switch': 'viewed',
        }
    )

def post_ranking_comment(request):
    most_commented =  Post.published.annotate(
        total_comments=Count('comments')
    ).filter(total_comments__gt=0).order_by('-total_comments')
    posts = paginate(request, most_commented)
    return render(
        request,
        'blog/ranking.html',
        {
            'posts': posts,
            'switch': 'commented',
            }
    )

def tag_list(request):
    tags = Tag.objects.all()
    return render(
        request,
        'blog/tag_list.html',
        {
            'tags': tags,
        },
    )


@login_required
def tag_create(request):
    form = TagForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
            messages.success(request, "Tag has been created!")
            return redirect('blog:tag_list')
        except TagAlreadyExist as e:
            messages.error(request, str(e))
    
    return render(
        request,
        'blog/tag_create.html',
        {'form': form},
    )

def user_detail(request, username):
    user = get_object_or_404(User, username=username, is_active=True)
    posts = Post.published.filter(author=user)
    posts = paginate(request, posts)
    return render(
        request,
        'users/detail.html',
        {
            'profile': user,
            'posts': posts,
        },
    )

@login_required
def user_draft(request):
    posts = Post.objects.filter(author=request.user, status='DF')
    posts = paginate(request, posts)
    return render(
        request,
        'users/detail.html',
        {
            'profile': request.user,
            'posts': posts,
        },
    )
