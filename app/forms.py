from django import forms
from .models import Comment, Post, Game, PostCategory
from tinymce.widgets import TinyMCE  # Impor TinyMCE

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full p-3 border-2 border-deep-brown-200 rounded-lg focus:outline-none focus:border-primary-accent focus:ring-1 focus:ring-primary-accent transition',
                'rows': 4,
                'placeholder': 'What are your thoughts?'
            })
        }
        labels = {
            'content': ''
        }

class PostForm(forms.ModelForm):
    game_title = forms.ModelChoiceField(
        queryset=Game.objects.all(),
        empty_label="Select a Game",
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full text-base px-4 py-3 border-2 border-deep-brown-200 rounded-lg bg-gray-50 focus:outline-none focus:border-primary-accent focus:ring-1 focus:ring-primary-accent transition'
        })
    )
    category = forms.ModelChoiceField(
        queryset=PostCategory.objects.all(),
        empty_label="Select a Category",
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full text-base px-4 py-3 border-2 border-deep-brown-200 rounded-lg bg-gray-50 focus:outline-none focus:border-primary-accent focus:ring-1 focus:ring-primary-accent transition'
        })
    )

    class Meta:
        model = Post
        fields = ['title', 'content', 'cover_image', 'game_title', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full text-lg px-4 py-3 border-2 border-deep-brown-200 rounded-lg bg-gray-50 focus:outline-none focus:border-primary-accent focus:ring-1 focus:ring-primary-accent transition',
                'placeholder': 'An interesting title...'
            }),
            # Konfigurasi TinyMCE disederhanakan, logika mention akan ditangani di template
            'content': TinyMCE(
                attrs={'cols': 80, 'rows': 30},
                mce_attrs={
                    'plugins': 'autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table paste help wordcount',
                    'toolbar': 'undo redo | blocks | bold italic | bullist numlist | link image | removeformat',
                    'height': 400,
                }
            ),
            'cover_image': forms.ClearableFileInput(attrs={
                'class': 'text-sm text-deep-brown-700'
            })
        }


class MessageForm(forms.Form):
    content = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'w-full flex-grow border rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-accent',
            'placeholder': 'Type a message...'
        })
    )
