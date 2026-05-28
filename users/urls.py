from django.urls import path

from . import views


urlpatterns = [
    path('signup', views.SignupPageView.as_view(), name='signup'),
    path('users/<username>/', views.user_detail, name='user_detail'),
]
