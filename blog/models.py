from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from taggit.managers import TaggableManager


class PostAlreadyExist(Exception):
    def __init__(self):
        self.message = "A post with the same title was already published today."
        super().__init__(self.message)
    

class DraftAlreadyExist(Exception):
    def __init__(self):
        self.message = "You already have a draft post with same title."
        super().__init__(self.message)


class PublishedManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset().filter(status=Post.Status.PUBLISHED)
        )

# Create your models here.
class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DF', 'Draft'
        PUBLISHED = 'PB', 'Published'
    title = models.CharField(max_length=250)
    slug = models.SlugField(
        max_length=250,
        unique_for_date='publish'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts'
    )
    status = models.CharField(
        max_length=2,
        choices=Status,
        default=Status.DRAFT
    )
    publish = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    body = models.TextField()

    objects = models.Manager()  # The default manager.
    published = PublishedManager()  # Our custom manager.
    tags = TaggableManager()

    class Meta:
        ordering = ['-publish']
        indexes = [
            models.Index(fields=['-publish']),
        ] 

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        if self.status == 'PB':
            if Post.published.filter(
            slug=self.slug,
            publish__date=timezone.localdate(),
            ).exists():
                raise PostAlreadyExist
            self.publish = timezone.now()
        else:
            if Post.objects.filter(
            slug=self.slug,
            author=self.author,
            ).exists():
                raise DraftAlreadyExist
            self.publish = None
        super().save(*args, **kwargs)


    def get_absolute_url(self):
        if self.status == 'PB':
            return reverse(
                'blog:post_detail',
                args=[
                    self.publish.year,
                    self.publish.month,
                    self.publish.day,
                    self.slug,
                ],
            )
        else:
            return reverse(
                'blog:draft_detail',
                args=[
                    self.slug,
                ],
            )
        
    def __str__(self):
        return self.title 


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    commented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    body = models.TextField() 
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['created']
        indexes = [
            models.Index(fields=['created']),
        ]

    def __str__(self):
        return f'Comment by {self.commented_by} on {self.post}'