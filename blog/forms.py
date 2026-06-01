from django import forms
from taggit.models import Tag

from .models import Comment, Post


class RestrictedTagField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queryset', Tag.objects.all())
        super().__init__(*args, **kwargs)


class PostForm(forms.ModelForm):
    tags = RestrictedTagField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple,
        # widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    class Meta:
        model = Post
        fields = ['title', 'body', 'status', 'tags',]


class EmailPostForm(forms.Form):
    name = forms.CharField(max_length=25)
    email = forms.EmailField()
    to = forms.EmailField()
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea
    )

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']

class SearchForm(forms.Form):
    query = forms.CharField()
