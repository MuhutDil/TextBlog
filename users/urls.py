from django.urls import path

from . import views


urlpatterns = [
    path('signup', views.SignupPageView.as_view(), name='signup'),
    path('users/<username>/', views.user_detail, name='user_detail'),
    path('draft/', views.user_draft, name='draft'),
    path('draft/<slug:post>', views.draft_detail, name='draft_detail'),
]
