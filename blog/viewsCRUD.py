from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib import messages
from functools import wraps

from .formsCRUD import PostCreateForm, PostUpdateForm
from .models import Post


def user_is_author(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        post = get_object_or_404(Post, id=kwargs['post_id'])
        
        # Check if the logged-in user is the author
        if post.author == request.user:
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You don't have permission to edit this post!")
            return redirect(post.get_absolute_url())
            
    return _wrapped_view


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostCreateForm(request.POST)
        # Same published post in this data doen't found
        if not Post.published.filter(
            slug=request.POST['title'], 
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
    
    else:
        form = PostCreateForm()
    return render(
        request,
        'blog/create.html',
        {'form': form},
    )


@login_required
@user_is_author
def post_update(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(
        Post,
        id=post_id,
        status=Post.Status.PUBLISHED
    )
    if request.method == 'POST':
        form = PostUpdateForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            messages.success(request, "Your post has been updated!")
            return redirect(post.get_absolute_url())
    else:
        form = PostUpdateForm(instance=post)
    return render(
        request,
        'blog/update.html',
        {
            'post': post,
            'form': form,
        },
    )


@login_required
@user_is_author
def post_delete(request, post_id):
    pass

