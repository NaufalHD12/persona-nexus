from django import forms
from .models import Comment, Post, Game, PostCategory, Report
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


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Provide additional details (optional)'}),
        }
        

class AdminGameForm(forms.ModelForm):
    # === PERBAIKAN: Jadikan slug tidak wajib diisi ===
    slug = forms.SlugField(required=False, help_text="Leave blank to auto-generate from the title.")

    class Meta:
        model = Game
        fields = ['title', 'description', 'slug', 'game_logo']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Persona 5 Royal'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'A brief description of the game.'}),
            'slug': forms.TextInput(attrs={'placeholder': 'auto-generated if left blank'}),
        }

class AdminCategoryForm(forms.ModelForm):
    # === PERBAIKAN: Jadikan slug tidak wajib diisi ===
    slug = forms.SlugField(required=False, help_text="Leave blank to auto-generate from the name.")
    
    class Meta:
        model = PostCategory
        fields = ['name', 'description', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Fan Art & Cosplay'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'A brief description of the category.'}),
            'slug': forms.TextInput(attrs={'placeholder': 'auto-generated if left blank'}),
        }