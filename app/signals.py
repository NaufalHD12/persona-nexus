from django.db.models.signals import post_save, m2m_changed, pre_save, post_delete
from django.dispatch import receiver
from .models import Comment, Notification, UserProfile, Vote, Post, Message, Conversation
from friendship.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
import re

# === Sinyal pre_save BARU untuk menyimpan mention lama ===
@receiver(pre_save, sender=Post)
@receiver(pre_save, sender=Comment)
def store_old_mentions(sender, instance, **kwargs):
    """
    Sebelum menyimpan, ambil daftar mention yang sudah ada dari database.
    """
    if instance.pk:  # Hanya berjalan jika objek sudah ada (sedang di-update)
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_content = old_instance.content
            old_mentioned_usernames = set(re.findall(r'@(\w+)', old_content))
            instance._old_mentions = old_mentioned_usernames
        except sender.DoesNotExist:
            instance._old_mentions = set()
    else:
        instance._old_mentions = set()

# === Logika di post_save DIPERBARUI untuk menangani update ===
@receiver(post_save, sender=Post)
@receiver(post_save, sender=Comment)
def create_mention_notifications(sender, instance, created, **kwargs):
    """
    Membuat notifikasi untuk mention baru saat create atau update.
    """
    content = instance.content
    current_mentioned_usernames = set(re.findall(r'@(\w+)', content))

    if created:
        # Jika objek baru dibuat, semua mention adalah baru
        newly_mentioned_usernames = current_mentioned_usernames
    else:
        # Jika objek diupdate, cari mention yang baru ditambahkan
        old_mentions = getattr(instance, '_old_mentions', set())
        newly_mentioned_usernames = current_mentioned_usernames - old_mentions

    if not newly_mentioned_usernames:
        return

    mentioned_users = UserProfile.objects.filter(username__in=newly_mentioned_usernames)
    content_type = ContentType.objects.get_for_model(instance)

    for user_to_notify in mentioned_users:
        if user_to_notify == instance.author:
            continue

        if isinstance(instance, Post):
            verb = "mentioned you in a post:"
        elif isinstance(instance, Comment):
            # Jika mention ada di dalam komentar, action_object seharusnya adalah Post
            # agar tautan notifikasi mengarah ke halaman postingan.
            verb = "mentioned you in a comment on:"
            action_object_for_notif = instance.post
        else:
            verb = "mentioned you in:"
            action_object_for_notif = instance

        # Periksa secara manual apakah notifikasi sudah ada
        existing_notification = Notification.objects.filter(
            recipient=user_to_notify,
            actor=instance.author,
            content_type=content_type,
            object_id=instance.id,
            notification_type=Notification.NotificationType.MENTION
        ).first()

        if not existing_notification:
            Notification.objects.create(
                recipient=user_to_notify,
                actor=instance.author,
                verb=verb,
                action_object=instance, # action_object tetap instance asli (Post/Comment)
                notification_type=Notification.NotificationType.MENTION
            )


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    """
    Membuat notifikasi saat ada komentar atau balasan baru.
    """
    if created:
        comment = instance
        post = comment.post
        
        if comment.parent:
            recipient = comment.parent.author
            if recipient != comment.author:
                Notification.objects.create(
                    recipient=recipient,
                    actor=comment.author,
                    verb="replied to your comment in",
                    action_object=post,
                    notification_type=Notification.NotificationType.NEW_REPLY
                )
        else:
            recipient = post.author
            if recipient != comment.author:
                Notification.objects.create(
                    recipient=recipient,
                    actor=comment.author,
                    verb="commented on your post",
                    action_object=post,
                    notification_type=Notification.NotificationType.NEW_COMMENT
                )

@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance, created, **kwargs):
    """
    Membuat notifikasi saat ada follower baru.
    """
    if created:
        Notification.objects.create(
            recipient=instance.followee,
            actor=instance.follower,
            verb="started following you.",
            notification_type=Notification.NotificationType.NEW_FOLLOWER
        )

@receiver(post_save, sender=Vote)
def create_vote_notification(sender, instance, created, **kwargs):
    """
    Membuat notifikasi saat ada upvote baru pada sebuah post.
    """
    if created and instance.value == Vote.UPVOTE:
        if isinstance(instance.content_object, Post):
            post = instance.content_object
            recipient = post.author
            actor = instance.user

            if recipient != actor:
                Notification.objects.create(
                    recipient=recipient,
                    actor=actor,
                    verb="upvoted your post",
                    action_object=post,
                    notification_type=Notification.NotificationType.POST_VOTE
                )

@receiver(m2m_changed, sender=UserProfile.saved_posts.through)
def create_save_post_notification(sender, instance, action, pk_set, **kwargs):
    """
    Membuat notifikasi saat seorang pengguna menyimpan postingan pengguna lain.
    """
    if action == "post_add":
        actor = instance
        post_id = list(pk_set)[0]
        post = Post.objects.get(pk=post_id)
        recipient = post.author

        if recipient != actor:
            Notification.objects.create(
                recipient=recipient,
                actor=actor,
                verb="saved your post",
                action_object=post,
                notification_type=Notification.NotificationType.POST_SAVE
            )


@receiver(post_save, sender=Vote)
@receiver(post_delete, sender=Vote)
def update_user_karma(sender, instance, **kwargs):
    """
    Update karma pengguna setiap kali vote dibuat atau dihapus.
    """
    content_object = instance.content_object
    
    # Pastikan objek yang divote (post/comment) masih ada
    if not content_object:
        return

    user_to_update = content_object.author
    
    # Hitung total skor dari semua post milik pengguna
    post_karma = Post.objects.filter(author=user_to_update).aggregate(
        total_score=Sum('votes__value')
    )['total_score'] or 0

    # Hitung total skor dari semua comment milik pengguna
    comment_karma = Comment.objects.filter(author=user_to_update).aggregate(
        total_score=Sum('votes__value')
    )['total_score'] or 0
    
    # Update total karma
    user_to_update.karma = post_karma + comment_karma
    user_to_update.save(update_fields=['karma'])


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Membuat notifikasi "lonceng" saat ada pesan baru.
    """
    if created:
        message = instance
        conversation = message.conversation
        sender = message.sender
        
        # Cari penerima pesan (semua peserta selain pengirim)
        for participant in conversation.participants.all():
            if participant != sender:
                Notification.objects.create(
                    recipient=participant,
                    actor=sender,
                    verb="sent you a new message.",
                    action_object=conversation, # Tautkan notifikasi ke percakapan
                    notification_type=Notification.NotificationType.NEW_MESSAGE
                )