from .models import Message

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