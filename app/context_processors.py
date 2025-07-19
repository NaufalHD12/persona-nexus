from .models import Message, Notification

def unread_messages_count(request):
    if request.user.is_authenticated:
        # Hitung pesan yang belum dibaca di mana pengguna adalah peserta,
        # dan bukan pengirim pesan tersebut.
        count = Message.objects.filter(
            conversation__participants=request.user, 
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        return {'unread_message_count': count}
    return {}

def notifications_context(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        # Ambil 5 notifikasi terbaru untuk ditampilkan di dropdown
        latest_notifications = Notification.objects.filter(
            recipient=request.user
        )[:5]

        return {
            'unread_notification_count': unread_count,
            'latest_notifications': latest_notifications
        }
    return {}