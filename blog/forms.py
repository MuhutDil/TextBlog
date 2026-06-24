from django import forms

from .models import Comment, Post, Tag


class RestrictedTagField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("queryset", Tag.objects.all())
        super().__init__(*args, **kwargs)


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title",
            "body",
            "status",
            "tags",
        ]
        widgets = {
            "status": forms.RadioSelect(),
            "tags": forms.CheckboxSelectMultiple(),
            "body": forms.Textarea(attrs={"rows": 5}),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]


class EmailPostForm(forms.Form):
    name = forms.CharField(max_length=25)
    email = forms.EmailField()
    to = forms.EmailField()
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 5}),
        }


class SearchForm(forms.Form):
    query = forms.CharField()
