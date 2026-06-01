from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import messages
from functools import wraps
from taggit.models import Tag

from .forms import CommentForm, EmailPostForm, SearchForm, PostForm
from .models import Post


POSTS_ON_PAGE = 3
COUNT_SIMILAR_POST = 4


def user_is_author(view_func):
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

@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if request.method == 'POST':
        slug = slugify(request.POST.get('title'))
        # Same published post in this data doen't found
        if not Post.published.filter(
            slug=slug,
            publish__date=timezone.localdate(),
        ).exists():
            if form.is_valid():
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                form.save_m2m()
                messages.success(request, "Your post has been created!")
                return redirect(post.get_absolute_url())
        messages.error(request, "A post with the same title was already published today.")
    
    return render(
        request,
        'blog/create.html',
        {'form': form},
    )

def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])
    paginator = Paginator(post_list, POSTS_ON_PAGE)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer get the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range get last page of results
        posts = paginator.page(paginator.num_pages)
    return render(
        request,
        'blog/list.html',
        {
            'posts': posts,
            'tag': tag,
        }
    )


def post_detail(request, year, month, day, post):
    post = get_object_or_404(
        Post,
        status=Post.Status.PUBLISHED,
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )
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
        },
    )



@user_is_author
def post_update(request, post_id, post=None):
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Your post has been updated!")
            return redirect(post.get_absolute_url())
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
    if request.method == "POST":
        post.delete()
        messages.success(request, "Your post has been deleted!")
        return redirect('/')
    return render(request, 'blog/confirm_delete.html', {'post': post})

@user_is_author
def draft_detail(request, post):
    post = get_object_or_404(
        Post,
        slug=post,
        status=Post.Status.DRAFT,
    )
    return render(
        request,
        'blog/detail.html',
        {
            'post': post,
        },
    )


def post_share(request, post_id):
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
def post_comment(request, post_id):
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
    return render(
        request,
        'blog/comment.html',
        {
            'post': post,
            'form': form,
            'comment': comment
        },
    )

def post_search(request):
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

    return render(
        request,
        'blog/search.html',
        {
            'form': form,
            'query': query,
            'results': results
        },
    )
