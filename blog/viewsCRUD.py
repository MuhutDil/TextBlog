from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.contrib import messages

from .formsCRUD import PostForm
from .models import Post


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
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
        form = PostForm()
    return render(
        request,
        'blog/create.html',
        {'form': form},
    )


@login_required
@user_passes_test(lambda u: u.is_author)
def post_update(request, post_id):
    pass


@login_required
@user_passes_test(lambda u: u.is_author)
def post_delete(request, post_id):
    pass

