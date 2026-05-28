from django.urls import reverse_lazy
from django.views import generic
from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse

from .forms import CustomUserCreationForm
from blog.models import Post


User = get_user_model()


class SignupPageView(generic.CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"
    
    def form_valid(self, form):
        messages.success(self.request, "Account created successfully!")
        return super().form_valid(form)


def user_detail(request, username):
    user = get_object_or_404(User, username=username, is_active=True)
    posts = Post.published.filter(author=user)
    return render(
        request,
        'users/detail.html',
        {
            'profile': user,
            'posts': posts,
        },
    )
