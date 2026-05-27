from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.text import slugify
from django.contrib import messages
from functools import wraps

from .formsCRUD import PostForm
from .models import Post


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
                post.slug = slug
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

