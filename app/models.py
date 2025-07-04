from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.urls import reverse
from django.utils.text import slugify


class PostCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    
    def __str__(self):
        return self.name
    
    def get_icon(self):
        icon_map = {
            'News & Announcements': 'bell',
            'Bug Reports & Support': 'tool',
            'Off Topic': 'message-circle',
            'Game Mechanics & Strategy': 'settings',
            'Characters & Personas': 'users',
            'Fanfiction & Lore': 'book-open',
            'Fan Art & Cosplay': 'image',
            'Guides & Tips': 'compass',
            'General Discussion': 'message-square'
        }
        return icon_map.get(self.name, 'tag')
    

class Game(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    slug = models.SlugField(max_length=100, unique=True)
    # Field baru untuk logo game
    game_logo = models.ImageField(upload_to='game_logos/', blank=True, null=True)
    
    def __str__(self):
        return self.title
    

class Vote(models.Model):
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_vote_per_user'
            )
        ]
    
    UPVOTE = 1
    DOWNVOTE = -1
    VOTE_CHOICES = (
        (UPVOTE, 'Upvote'),
        (DOWNVOTE, 'Downvote'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    value = models.IntegerField(choices=VOTE_CHOICES)    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)


class Post(models.Model):
    
    class Meta:
        ordering = ['-created_at']
        
    title = models.CharField(max_length=255)
    
    # PERBAIKAN: Tambahkan unique=True dan blank=True
    # null=True juga bisa ditambahkan untuk migrasi awal jika ada data
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    content = models.TextField()
    cover_image = models.ImageField(upload_to='post_covers/', blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts')
    game_title = models.ForeignKey(
        'Game', # Gunakan string untuk menghindari circular import
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name='posts'
    )
    category = models.ForeignKey(
        'PostCategory', # Gunakan string untuk menghindari circular import
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name='posts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    votes = GenericRelation('Vote') # Gunakan string untuk menghindari circular import
    
    @property
    def vote_score(self):
        return self.votes.aggregate(score=Sum('value'))['score'] or 0
    
    def save(self, *args, **kwargs):
        # Generate slug dari title jika slug belum ada.
        if not self.slug:
            self.slug = slugify(self.title)

        # Logika untuk memastikan slug selalu unik.
        original_slug = self.slug
        counter = 1
        
        # Bangun queryset awal untuk memeriksa keunikan.
        queryset = Post.objects.filter(slug=self.slug)
        # Jika kita sedang memperbarui objek yang sudah ada, kecualikan objek ini dari pemeriksaan.
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        # Lakukan loop sampai kita menemukan slug yang unik.
        while queryset.exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            # Periksa lagi dengan slug yang baru.
            queryset = Post.objects.filter(slug=self.slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('post_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return self.title
    

class UserProfile(AbstractUser):
    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(
        upload_to='avatars/', 
        default='avatars/default.png',
        blank=True,
        null=True
    )
    saved_posts = models.ManyToManyField(
        Post, 
        related_name="saved_by_users", # Nama untuk mengakses dari sisi Post
        blank=True
    )
    
    def __str__(self):
        return self.username
    
    @property
    def avatar_url(self):
        """Helper method untuk mendapatkan URL avatar"""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        # Sebaiknya gunakan static untuk default image, tapi ini juga bisa
        return f"{settings.STATIC_URL}images/avatars/default.png"



class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies') # Relasi ke komentar lain untuk membuat balasan berantai
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'
    

class Conversation(models.Model):
    """Mewakili satu sesi percakapan antara dua pengguna."""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name="conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    """Mewakili satu pesan di dalam sebuah percakapan."""
    # Field ini harus ada dan bernama 'conversation'
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="sent_messages"
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"