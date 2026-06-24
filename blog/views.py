from functools import wraps

import redis
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CommentForm, EmailPostForm, PostForm, SearchForm, TagForm
from .models import DraftAlreadyExist, Post, PostAlreadyExist, Tag, TagAlreadyExist

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
        post = get_object_or_404(Post, id=kwargs["post_id"])

        # Check if the logged-in user is the author
        if post.author == request.user:
            kwargs["post"] = post
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You don't have access to this post!")
            return redirect(post.get_absolute_url())

    return _wrapped_view


def paginate(request, object_list, per_page=POSTS_ON_PAGE):
    """
    Paginate a list or queryset of objects based on the request's page parameter.

    This helper function handles the common pagination pattern across multiple views.
    It extracts the page number from the GET parameters, validates it, and returns
    the appropriate page of objects.

    Args:
        request: Django HttpRequest object containing GET parameters
        object_list: A list, tuple, or QuerySet of objects to paginate
        per_page (int): Number of items per page. Defaults to POSTS_ON_PAGE setting.

    Returns:
        Page: A Django Paginator Page object containing the paginated items

    Behavior:
        - Non-integer page numbers return the first page
        - Out-of-range page numbers return the last page
    """
    paginator = Paginator(object_list, per_page)
    page_number = request.GET.get("page", 1)
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
    if request.method == "POST" and form.is_valid():
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
        "blog/create.html",
        {"form": form},
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
        "blog/list.html",
        {
            "posts": posts,
            "tag": tag,
        },
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
    total_views = r.incr(f"post:{post.id}:views")
    r.zincrby("posts_ranking", 1, post.id)
    # List of active comments for this post
    comments = post.comments.filter(active=True)
    # Form for users to comment
    form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list("id", flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-publish"
    )[:COUNT_SIMILAR_POST]

    return render(
        request,
        "blog/detail.html",
        {
            "post": post,
            "comments": comments,
            "form": form,
            "similar_posts": similar_posts,
            "total_views": total_views,
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
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Your post has been updated!")
            return redirect(post.get_absolute_url())
        except (PostAlreadyExist, DraftAlreadyExist) as e:
            messages.error(request, str(e))
    return render(
        request,
        "blog/update.html",
        {
            "post": post,
            "form": form,
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
        return redirect("/")
    return render(request, "blog/confirm_delete.html", {"post": post})


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
        "blog/detail.html",
        {
            "post": post,
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
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False

    if request.method == "POST":
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = f"{cd['name']} ({cd['email']}) recommends you read {post.title}"
            message = (
                f"Read {post.title} at {post_url}\n\n"
                f"{cd['name']}'s comments: {cd['comments']}"
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[cd["to"]],
            )
            sent = True

    else:
        form = EmailPostForm()
    return render(
        request,
        "blog/share.html",
        {"post": post, "form": form, "sent": sent},
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
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
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

    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            results = (
                Post.published.annotate(
                    similarity=TrigramSimilarity("title", query),
                )
                .filter(similarity__gt=0.1)
                .order_by("-similarity")
            )
            results = paginate(request, results)

    return render(
        request,
        "blog/search.html",
        {"form": form, "query": query, "results": results},
    )


def post_ranking_view(request):
    """
    Display most viewed posts based on Redis ranking data.

    Retrieves post IDs from a Redis sorted set that tracks view counts, fetches
    the corresponding Post objects from the database, and preserves the original
    ranking order. Results are paginated for display.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Rendered ranking.html template with:
            - 'posts': Paginated page of viewed posts
            - 'switch': String 'viewed' to indicate the ranking type
    """
    post_ranking = r.zrange("posts_ranking", 0, -1, desc=True)
    post_ranking_ids = [int(id) for id in post_ranking]
    most_viewed = list(Post.published.filter(id__in=post_ranking_ids))
    most_viewed.sort(key=lambda x: post_ranking_ids.index(x.id))
    posts = paginate(request, most_viewed)
    return render(
        request,
        "blog/ranking.html",
        {
            "posts": posts,
            "switch": "viewed",
        },
    )


def post_ranking_comment(request):
    """
    Display posts ranked by the number of comments they have received.

    Annotates each published post with a comment count, filters to posts with
    at least one comment, and orders them from most to least commented. Results
    are paginated for display.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Rendered ranking.html template with:
            - 'posts': Paginated page of posts ordered by comment count
            - 'switch': String 'commented' to indicate the ranking type
    """
    most_commented = (
        Post.published.annotate(total_comments=Count("comments"))
        .filter(total_comments__gt=0)
        .order_by("-total_comments")
    )
    posts = paginate(request, most_commented)
    return render(
        request,
        "blog/ranking.html",
        {
            "posts": posts,
            "switch": "commented",
        },
    )


def tag_list(request):
    """
    Display a list of tags with optional fuzzy search functionality.

    If a search query is provided and valid, performs a trigram similarity search
    on tag names to find matches above a 0.3 threshold. Otherwise, displays all
    tags alphabetically. The search form is preserved in the context for
    displaying search input and errors.

    Args:
        request: Django HttpRequest object with optional 'query' GET parameter

    Returns:
        HttpResponse: Rendered tag_list.html template with:
            - 'form': SearchForm instance (bound or unbound)
            - 'query': The search query string or None if no search was performed
            - 'tags': QuerySet of Tag objects (filtered or all)
    """
    form = SearchForm(request.GET or None)
    query = None
    if "query" in request.GET and form.is_valid():
        query = form.cleaned_data["query"]
        tags = (
            Tag.objects.annotate(
                similarity=TrigramSimilarity("name", query),
            )
            .filter(similarity__gt=0.3)
            .order_by("name")
        )
    else:
        tags = Tag.objects.all().order_by("name")
    return render(
        request,
        "blog/tag_list.html",
        {"form": form, "query": query, "tags": tags},
    )


@login_required
def tag_create(request):
    """
    Handle creation of new tags via a form with validation and error handling.

    Displays a form for creating new tags. On valid POST submission, saves the
    tag and redirects to the tag list with a success message. Handles the custom
    TagAlreadyExist exception by displaying an error message without redirecting.

    Args:
        request: Django HttpRequest object (POST for form submission, GET for display)

    Returns:
        HttpResponse:
            - On GET or invalid form: Rendered tag_create.html template with form
            - On successful POST: Redirects to 'blog:tag_list' with success message
            - On TagAlreadyExist: Rendered tag_create.html template with form and error message

    Raises:
        TagAlreadyExist: Custom exception caught and handled with error message
    """
    form = TagForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Tag has been created!")
            return redirect("blog:tag_list")
        except TagAlreadyExist as e:
            messages.error(request, str(e))

    return render(
        request,
        "blog/tag_create.html",
        {"form": form},
    )


def user_detail(request, username):
    """
    Display a public user profile with their published posts.

    Fetches an active user by username and displays all of their published posts
    in paginated format. Returns 404 if the user does not exist or is inactive.

    Args:
        request: Django HttpRequest object
        username (str): The username of the user to display

    Returns:
        HttpResponse: Rendered users/detail.html template with:
            - 'profile': User object (active user)
            - 'posts': Paginated page of published posts by this user

    Raises:
        Http404: If no active user exists with the given username
    """
    user = get_object_or_404(User, username=username, is_active=True)
    user_posts = Post.published.filter(author=user)
    posts = paginate(request, user_posts)
    return render(
        request,
        "users/detail.html",
        {
            "profile": user,
            "posts": posts,
        },
    )


@login_required
def user_draft(request):
    """
    Display the current user's draft posts.

    Shows all posts with 'DF' (draft) status that belong to the currently
    authenticated user. Results are paginated for display.

    Args:
        request: Django HttpRequest object

    Returns:
        HttpResponse: Rendered users/detail.html template with:
            - 'profile': The current authenticated user
            - 'posts': Paginated page of draft posts by this user
    """
    posts = Post.objects.filter(author=request.user, status="DF")
    posts = paginate(request, posts)
    return render(
        request,
        "users/detail.html",
        {
            "profile": request.user,
            "posts": posts,
        },
    )
