from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Comment, Notification, UserProfile, Vote, Post
from friendship.models import Follow

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    """
    Membuat notifikasi saat ada komentar atau balasan baru.
    """
    if created:
        comment = instance
        post = comment.post
        
        # Skenario 1: Balasan untuk komentar lain
        if comment.parent:
            recipient = comment.parent.author
            # Jangan kirim notif jika membalas komentar sendiri
            if recipient != comment.author:
                Notification.objects.create(
                    recipient=recipient,
                    actor=comment.author,
                    verb="replied to your comment in",
                    action_object=post,
                    notification_type=Notification.NotificationType.NEW_REPLY
                )
        # Skenario 2: Komentar baru di sebuah postingan
        else:
            recipient = post.author
            # Jangan kirim notif jika mengomentari postingan sendiri
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
    # Kita hanya peduli pada upvote baru
    if created and instance.value == Vote.UPVOTE:
        post = instance.content_object
        recipient = post.author
        actor = instance.user

        # Jangan kirim notifikasi jika user me-vote postingannya sendiri
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
    # Kita hanya peduli saat sebuah postingan ditambahkan ke daftar simpan
    if action == "post_add":
        # instance di sini adalah UserProfile yang menyimpan post
        actor = instance
        
        # pk_set berisi ID dari post yang baru saja disimpan
        post_id = list(pk_set)[0]
        post = Post.objects.get(pk=post_id)
        recipient = post.author

        # Jangan kirim notifikasi jika user menyimpan postingannya sendiri
        if recipient != actor:
            Notification.objects.create(
                recipient=recipient,
                actor=actor,
                verb="saved your post",
                action_object=post,
                notification_type=Notification.NotificationType.POST_SAVE
            )
