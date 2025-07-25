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
    # === FIELD BARU DITAMBAHKAN ===
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    
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

    # === METODE SAVE DITAMBAHKAN ===
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})
    

class Game(models.Model):
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    slug = models.SlugField(max_length=100, unique=True, blank=True) # blank=True ditambahkan
    game_logo = models.ImageField(upload_to='game_logos/', blank=True, null=True)
    
    def __str__(self):
        return self.title
    
    # === METODE SAVE DITAMBAHKAN UNTUK AUTO-SLUG ===
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('game_detail', kwargs={'slug': self.slug})
    

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
    
    following_games = models.ManyToManyField(
        'Game',
        related_name="followers",
        blank=True
    )
    following_categories = models.ManyToManyField(
        'PostCategory',
        related_name="followers",
        blank=True
    )
    
    karma = models.IntegerField(default=0)
    
    def __str__(self):
        return self.username
    
    def get_absolute_url(self):
        return reverse('profile_detail', kwargs={'username': self.username})

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
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
    
    votes = GenericRelation('Vote')

    @property
    def vote_score(self):
        return self.votes.aggregate(score=Sum('value'))['score'] or 0
    
    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'
    
    def get_absolute_url(self):
        return self.post.get_absolute_url() + f'#comment-{self.id}'
    

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
        
    def get_absolute_url(self):
        return reverse('conversation_detail', kwargs={'pk': self.pk})

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

    is_read = models.BooleanField(default=False)
    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"
    

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_MESSAGE = 'message', 'New Message'
        POST_VOTE = 'vote', 'Post Vote'
        NEW_COMMENT = 'comment', 'New Comment'
        NEW_REPLY = 'reply', 'New Reply'
        NEW_FOLLOWER = 'follower', 'New Follower'
        POST_SAVE = 'save', 'Post Save'
        MENTION = 'mention', 'Mention'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="actions")
    verb = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    action_object = GenericForeignKey('content_type', 'object_id')
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        # String representation sederhana untuk admin dan debugging
        return f"{self.actor} {self.verb}"

    # === PROPERTY BARU UNTUK MENAMPILKAN TEKS NOTIFIKASI YANG BENAR ===
    @property
    def summary_text(self):
        """
        Menghasilkan teks ringkasan yang bersih untuk ditampilkan di template.
        """
        verb = self.verb
        target = self.action_object

        # Kasus 1: Notifikasi tanpa objek target (Pesan, Follower)
        if self.notification_type in [self.NotificationType.NEW_MESSAGE, self.NotificationType.NEW_FOLLOWER]:
            return verb

        if not target:
            return verb # Fallback

        # Kasus 2: Jika targetnya adalah Komentar (misal: mention di komentar)
        if isinstance(target, Comment):
            return f'{verb} "{target.post.title}"'

        # Kasus 3: Untuk Post dan objek lain yang punya judul
        if hasattr(target, 'title') and target.title:
            return f'{verb} "{target.title}"'
        
        # Fallback untuk kasus lain (misal: Conversation)
        return verb

    def get_absolute_url(self):
        """
        Membuat URL yang benar berdasarkan tipe notifikasi.
        """
        if self.notification_type == self.NotificationType.NEW_MESSAGE and self.action_object:
            return self.action_object.get_absolute_url()

        if hasattr(self.action_object, 'get_absolute_url'):
            if self.notification_type == self.NotificationType.MENTION:
                return self.action_object.get_absolute_url()
            elif isinstance(self.action_object, Comment):
                return self.action_object.post.get_absolute_url()
            else:
                return self.action_object.get_absolute_url()

        elif self.notification_type == self.NotificationType.NEW_FOLLOWER and self.actor:
            return reverse('profile_detail', kwargs={'username': self.actor.username})
        
        return reverse('notification_list')


class Report(models.Model):
    class ReportReason(models.TextChoices):
        SPAM = 'SPAM', 'Spam or Misleading'
        HARASSMENT = 'HARASSMENT', 'Harassment or Hate Speech'
        INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate Content'
        OTHER = 'OTHER', 'Other'

    class ReportStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        REVIEWED_ACTION_TAKEN = 'ACTION_TAKEN', 'Reviewed - Action Taken'
        REVIEWED_NO_ACTION = 'NO_ACTION', 'Reviewed - No Action'

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    reason = models.CharField(max_length=20, choices=ReportReason.choices)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic Foreign Key untuk menunjuk ke Post atau Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Report by {self.reporter.username} on {self.content_type.model} ({self.object_id})"