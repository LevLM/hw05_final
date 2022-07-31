from django import forms
from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):

    class Meta:
        model = Post
        fields = ('group', 'text', 'image')


class CommentForm(ModelForm):

    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'cols': 30, 'rows': 5})
        }
