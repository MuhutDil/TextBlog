from django.urls import path

from . import views, viewsCRUD

app_name = 'blog'

POST_LINK = '<int:year>/<int:month>/<int:day>/<slug:post>/'

urlpatterns = [
    path('', views.post_list, name='home'),
    path('create/', viewsCRUD.post_create, name='post_create'),
    # path('', views.PostListView.as_view(), name='post_list'),
    path(
        'tag/<slug:tag_slug>/', views.post_list, name='post_list_by_tag'
    ),
    path(
        POST_LINK,
        views.post_detail,
        name='post_detail',
    ),
    path('<int:post_id>/share/', views.post_share, name='post_share'),
    path(
        '<int:post_id>/comment/', views.post_comment, name='post_comment'
    ),
    path('search/', views.post_search, name='post_search'),
]