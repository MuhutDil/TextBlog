from django import forms
from taggit.models import Tag

from .models import Post

class RestrictedTagField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('queryset', Tag.objects.all())
        super().__init__(*args, **kwargs)

    # def clean(self, value):
    #     tags = super().clean(value)
    #     return [tag.name for tag in tags]


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
