from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from taggit.managers import TaggableManager


class PostAlreadyExist(Exception):
    """
    Exception raised when attempting to publish a second post with the same title on the same day.
    
    This exception prevents duplicate published posts from being created on the same date.
    """
    def __init__(self):
        self.message = "A post with the same title was already published today."
        super().__init__(self.message)
    

class DraftAlreadyExist(Exception):
    """
    Exception raised when attempting to create a second draft with the same title.
    
    This exception prevents duplicate draft posts from being created by the same author.
    """
    def __init__(self):
        self.message = "You already have a draft post with same title."
        super().__init__(self.message)


class PublishedManager(models.Manager):
    """
    Custom model manager that returns only published posts.
    
    This manager provides a filtered queryset containing only posts with
    status set to PUBLISHED, simplifying queries for published content.
    """
    def get_queryset(self):
        """
        Return queryset filtered to only include published posts.
        
        Returns:
            QuerySet: Queryset containing only posts with PUBLISHED status.
        """
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
        """
        Override the save method to handle slug generation and duplicate prevention.
        
        This method generates a slug from the title, then checks for duplicates:
        - For published posts: Prevents duplicate titles on the same date
        - For draft posts: Prevents duplicate drafts by the same author
        
        It also sets the publish timestamp to now() when a post is published,
        or sets it to None when a post is saved as a draft.
        
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
            
        Raises:
            PostAlreadyExist: If a published post with same slug and date exists.
            DraftAlreadyExist: If a draft with same slug and author exists.
        """
        self.slug = slugify(self.title)
        if self.status == 'PB':
            self._check_published_dublicate()
            self.publish = self.publish or timezone.now()
        else:
            self._check_draft_dublicate()
            self.publish = None
        super().save(*args, **kwargs)

    def _check_published_dublicate(self):
        if Post.published.filter(
            slug=self.slug,
            publish__date=timezone.localdate(),
            ).exclude(id=self.id).exists():
                raise PostAlreadyExist

    def _check_draft_dublicate(self):
        if Post.objects.filter(
            slug=self.slug,
            author=self.author,
            status=Post.Status.DRAFT
            ).exclude(id=self.id).exists():
                raise DraftAlreadyExist
        

    def get_absolute_url(self):
        """
        Generate the canonical URL for this post.
        
        Returns a URL string that points to either the published post detail
        page (including date components) or the draft detail page based on
        the post's current status.
        
        Returns:
            str: URL path to the post's detail view.
        """
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