from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, AccessMixin
from django.contrib.contenttypes.models import ContentType
from .models import Notification, Post, Game, Report, Vote, PostCategory, Comment, UserProfile, Conversation, Message
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView, TemplateView
from django.db.models import OuterRef, Subquery, Count, Q, Sum
from .forms import AdminCategoryForm, AdminGameForm, CommentForm, PostForm, MessageForm, ReportForm
from django.urls import reverse, reverse_lazy
from friendship.models import Follow
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import json
from django.db.models.functions import TruncDay
from django.core.paginator import Paginator


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return ["app/home.html"]

    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            score=Sum('votes__value', default=0)
        )

        sort_by = self.request.GET.get('sort', 'new')
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        if sort_by == 'hot':
            queryset = queryset.order_by('-score', '-created_at')
        elif sort_by == 'top':
            queryset = queryset.order_by('-score')
        else:
            queryset = queryset.order_by('-created_at')

        if self.request.user.is_authenticated:
            user_vote = Vote.objects.filter(user=self.request.user, object_id=OuterRef('pk'), content_type__model='post').values('value')
            queryset = queryset.annotate(user_vote_value=Subquery(user_vote[:1]))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # === PERUBAHAN: Ambil 9 game secara acak untuk rotasi ===
        context['featured_games'] = Game.objects.order_by('?')[:9]
        context['popular_categories'] = PostCategory.objects.annotate(num_posts=Count('posts')).order_by('-num_posts')[:4]
        return context

    

class FollowingPostListView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return ["app/following.html"]

    def get_queryset(self):
        user = self.request.user
        
        # === LOGIKA BARU UNTUK FEED FOLLOWING ===
        following_users = Follow.objects.following(user)
        following_games = user.following_games.all()
        following_categories = user.following_categories.all()

        # Buat filter gabungan menggunakan Q objects
        filters = Q(author__in=following_users) | \
                  Q(game_title__in=following_games) | \
                  Q(category__in=following_categories)
        
        # Jika tidak ada yang diikuti, kembalikan queryset kosong
        if not (following_users or following_games or following_categories):
            return Post.objects.none()

        queryset = Post.objects.filter(filters).distinct().annotate(
             score=Sum('votes__value', default=0)
        )
        
        sort_by = self.request.GET.get('sort', 'new')
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))
        
        if sort_by == 'hot':
            queryset = queryset.order_by('-score', '-created_at')
        elif sort_by == 'top':
            queryset = queryset.order_by('-score')
        else:
            queryset = queryset.order_by('-created_at')

        user_vote = Vote.objects.filter(user=self.request.user, object_id=OuterRef('pk'), content_type__model='post').values('value')
        queryset = queryset.annotate(user_vote_value=Subquery(user_vote[:1]))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_games'] = Game.objects.order_by('?')[:9]
        context['popular_categories'] = PostCategory.objects.annotate(
            num_posts=Count('posts')
        ).order_by('-num_posts')[:4]
        return context


class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'app/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'author',
            'game_title',
            'category',
            'comments__author',
            'comments__replies'
        )
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['post']
        if self.request.user.is_authenticated:
            user_vote = post.votes.filter(user=self.request.user).first()
            post.user_vote_value = user_vote.value if user_vote else None
            
        # === PERUBAHAN: Anotasi vote pengguna pada setiap komentar ===
        comments_qs = post.comments.filter(parent__isnull=True).order_by('created_at')
        if self.request.user.is_authenticated:
            user_vote_subquery = Vote.objects.filter(
                user=self.request.user,
                content_type=ContentType.objects.get_for_model(Comment),
                object_id=OuterRef('pk')
            ).values('value')
            comments_qs = comments_qs.annotate(
                user_vote_value=Subquery(user_vote_subquery[:1])
            )

        context['comments_with_votes'] = comments_qs
        context['comment_form'] = CommentForm()
        return context

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'app/post_update_form.html'
    slug_url_kwarg = 'slug' # Mencari post berdasarkan slug dari URL

    def test_func(self):
        return self.request.user == self.get_object().author

    def form_valid(self, form):
        messages.success(self.request, f'Post "{self.object.title}" has been successfully updated.')
        return super().form_valid(form)

    def get_success_url(self):
        # Arahkan kembali ke halaman detail post setelah berhasil di-update
        return reverse_lazy('post_detail', kwargs={'slug': self.object.slug})

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'app/post_confirm_delete.html'
    success_url = reverse_lazy('home')
    slug_url_kwarg = 'slug'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def get(self, request, *args, **kwargs):
        if request.htmx:
            self.object = self.get_object()
            return render(request, 'app/partials/_confirm_delete_modal.html', {'post': self.object})
        return super().get(request, *args, **kwargs)

    # ==> PERBARUI METHOD POST <==
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        # Alih-alih redirect, kirim kembali modal sukses
        return render(request, 'app/partials/_success_modal.html', {
            'message': 'Your post has been successfully deleted.'
        })
    
    
class AddCommentView(LoginRequiredMixin, View):
    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug)
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(Comment, id=parent_id)
            comment.save()
            messages.success(request, 'Your comment has been successfully added.')
        else:
            messages.error(request, 'There was an error posting your comment.')

        return redirect('post_detail', slug=post.slug)


class GameListView(ListView):
    template_name = 'app/games.html'
    model = Game
    context_object_name = 'games'
    
# === VIEW BARU ===
class GameDetailView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10
    template_name = 'app/game_detail.html'

    def get_template_names(self):
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return [self.template_name]

    def get_queryset(self):
        # Ambil game berdasarkan slug dari URL
        self.game = get_object_or_404(Game, slug=self.kwargs['slug'])
        
        # Filter postingan hanya untuk game ini
        queryset = Post.objects.filter(game_title=self.game).annotate(
            score=Sum('votes__value', default=0)
        )

        sort_by = self.request.GET.get('sort', 'new')
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        if sort_by == 'hot':
            queryset = queryset.order_by('-score', '-created_at')
        elif sort_by == 'top':
            queryset = queryset.order_by('-score')
        else:
            queryset = queryset.order_by('-created_at')

        if self.request.user.is_authenticated:
            user_vote = Vote.objects.filter(
                user=self.request.user, 
                object_id=OuterRef('pk'), 
                content_type__model='post'
            ).values('value')
            queryset = queryset.annotate(user_vote_value=Subquery(user_vote[:1]))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['game'] = self.game
        context['is_following'] = self.request.user.following_games.filter(pk=self.game.pk).exists()
        return context


class CategoryDetailView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10
    template_name = 'app/category_detail.html'

    def get_template_names(self):
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return [self.template_name]

    def get_queryset(self):
        # Ambil kategori berdasarkan slug dari URL
        self.category = get_object_or_404(PostCategory, slug=self.kwargs['slug'])
        
        # Filter postingan hanya untuk kategori ini
        queryset = Post.objects.filter(category=self.category).annotate(
            score=Sum('votes__value', default=0)
        )

        sort_by = self.request.GET.get('sort', 'new')
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        if sort_by == 'hot':
            queryset = queryset.order_by('-score', '-created_at')
        elif sort_by == 'top':
            queryset = queryset.order_by('-score')
        else:
            queryset = queryset.order_by('-created_at')

        if self.request.user.is_authenticated:
            user_vote = Vote.objects.filter(
                user=self.request.user, 
                object_id=OuterRef('pk'), 
                content_type__model='post'
            ).values('value')
            queryset = queryset.annotate(user_vote_value=Subquery(user_vote[:1]))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['is_following'] = self.request.user.following_categories.filter(pk=self.category.pk).exists()
        return context
    
    
class ToggleGameFollowView(LoginRequiredMixin, View):
    def post(self, request, slug):
        game = get_object_or_404(Game, slug=slug)
        user = request.user
        
        if game in user.following_games.all():
            user.following_games.remove(game)
        else:
            user.following_games.add(game)
            
        return render(request, 'app/partials/_follow_game_button.html', {
            'game': game,
            'is_following': user.following_games.filter(pk=game.pk).exists()
        })


class ToggleCategoryFollowView(LoginRequiredMixin, View):
    def post(self, request, slug):
        category = get_object_or_404(PostCategory, slug=slug)
        user = request.user
        
        if category in user.following_categories.all():
            user.following_categories.remove(category)
        else:
            user.following_categories.add(category)
            
        return render(request, 'app/partials/_follow_category_button.html', {
            'category': category,
            'is_following': user.following_categories.filter(pk=category.pk).exists()
        })
    

class CategoryListView(ListView):
    template_name = 'app/categories.html'
    model = PostCategory
    context_object_name = 'categories'    
    

class VoteView(LoginRequiredMixin, View):
    
    def post(self, request, model_name, pk, direction):
        try:
            model = ContentType.objects.get(model=model_name).model_class()
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid model name'}, status=400)
        
        content_object = get_object_or_404(model, pk=pk)
        user = request.user
        vote_value = Vote.UPVOTE if direction == 'up' else Vote.DOWNVOTE

        existing_vote = Vote.objects.filter(
            user=user,
            content_type=ContentType.objects.get_for_model(content_object),
            object_id=content_object.id
        ).first()

        # === PERBAIKAN LOGIKA INTI ===
        if existing_vote:
            # Jika pengguna mengklik tombol yang sama, batalkan vote (hapus)
            if existing_vote.value == vote_value:
                existing_vote.delete()
            # Jika pengguna mengklik tombol yang berlawanan, ubah vote
            else:
                # Sebelum mengubah ke downvote, periksa apakah skor akan menjadi negatif
                # Skor saat ini adalah 1 (karena ada upvote), jika diubah jadi downvote, skor jadi -1.
                # Kita harus mencegah ini. Skor efektif setelah menghapus upvote adalah 0.
                if vote_value == Vote.DOWNVOTE and content_object.vote_score <= 1:
                    return JsonResponse({'error': 'Cannot downvote below zero.'}, status=403)
                existing_vote.value = vote_value
                existing_vote.save()
        else:
            # Jika ini adalah vote baru
            # Periksa apakah ini downvote pada skor 0 atau kurang
            if vote_value == Vote.DOWNVOTE and content_object.vote_score <= 0:
                return JsonResponse({'error': 'Cannot downvote below zero.'}, status=403)
            
            Vote.objects.create(
                user=user,
                content_object=content_object,
                value=vote_value
            )

        # Selalu hitung ulang skor akhir dari database sebagai sumber kebenaran
        final_score = content_object.vote_score
        
        # Dapatkan status vote pengguna saat ini untuk dikirim kembali ke frontend
        current_user_vote = Vote.objects.filter(
            user=user,
            content_type=ContentType.objects.get_for_model(content_object),
            object_id=content_object.id
        ).first()
        
        user_vote_status = 'none'
        if current_user_vote:
            user_vote_status = 'up' if current_user_vote.value == Vote.UPVOTE else 'down'

        return JsonResponse({
            'success': True,
            'score': final_score,
            'user_vote_status': user_vote_status
        })
        
        
class SettingsView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    fields = ['avatar', 'bio'] 
    template_name = 'account/settings.html'
    success_url = reverse_lazy('account_settings')

    def get_object(self, queryset=None):
        # Pastikan pengguna hanya bisa mengedit profil mereka sendiri
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been successfully updated.')
        return super().form_valid(form)
    
    
class PostCreateView(LoginRequiredMixin, CreateView):
    template_name = 'app/create_post.html'
    model = Post
    form_class = PostForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        # Set author postingan secara otomatis ke pengguna yang sedang login
        form.instance.author = self.request.user
        messages.success(self.request, 'Your post has been successfully created!')
        return super().form_valid(form)
    
    
class ProfileDetailView(DetailView):
    model = UserProfile
    template_name = 'app/profile_detail.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        
        # Ambil data yang sudah ada
        context['posts'] = profile_user.posts.all().order_by('-created_at')
        if self.request.user == profile_user:
            context['saved_posts'] = profile_user.saved_posts.all().order_by('-created_at')
        
        # === TAMBAHKAN DATA BARU UNTUK PROFIL ===
        context['comments'] = profile_user.comments.all().order_by('-created_at')
        context['followers'] = Follow.objects.followers(profile_user)
        context['following'] = Follow.objects.following(profile_user)
        context['followers_count'] = len(context['followers'])
        context['following_count'] = len(context['following'])
        
        is_following = False
        if self.request.user.is_authenticated and self.request.user != profile_user:
            is_following = Follow.objects.follows(self.request.user, profile_user)
        
        context['is_following'] = is_following
        return context


class FollowToggleView(LoginRequiredMixin, View):
    def post(self, request, username):
        target_user = get_object_or_404(UserProfile, username=username)

        if request.user != target_user:
            is_following = Follow.objects.follows(request.user, target_user)
            if is_following:
                Follow.objects.remove_follower(request.user, target_user)
            else:
                Follow.objects.add_follower(request.user, target_user)
        
        return redirect('profile_detail', username=target_user.username)

class SavePostToggleView(LoginRequiredMixin, View):
    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug)
        user = request.user
        
        if post in user.saved_posts.all():
            user.saved_posts.remove(post)
        else:
            user.saved_posts.add(post)
            
        return render(request, 'app/partials/_save_button.html', {'post': post})
    
    
class SuccessModalView(LoginRequiredMixin, TemplateView):
    """
    View ini hanya bertugas untuk menampilkan modal sukses.
    Pesan di dalam modal diambil dari parameter URL.
    """
    template_name = "app/partials/_success_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = self.request.GET.get('message', 'Your action was successful.')
        return context


class InboxView(LoginRequiredMixin, TemplateView):
    """
    Satu-satunya view yang menangani seluruh halaman pesan.
    """
    template_name = 'app/inbox.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # === PERBAIKAN: Anotasi setiap percakapan dengan jumlah pesan yang belum dibaca ===
        conversations = user.conversations.annotate(
            unread_count=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user)
            )
        ).order_by('-updated_at')
        
        context['conversations'] = conversations
        
        if 'pk' in kwargs:
            conversation = get_object_or_404(
                Conversation, 
                pk=kwargs['pk'], 
                participants=user
            )
            context['conversation'] = conversation
            context['message_form'] = MessageForm()
            
            # Tandai pesan di percakapan ini sebagai "telah dibaca"
            conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
        
        return context

class StartConversationView(LoginRequiredMixin, View):
    """
    Mencari atau membuat percakapan baru, lalu mengarahkan ke inbox.
    """
    def get(self, request, username):
        target_user = get_object_or_404(UserProfile, username=username)
        if target_user == request.user:
            return redirect('message_inbox')

        conversation = Conversation.objects.annotate(
            p_count=Count('participants')
        ).filter(
            p_count=2,
            participants=request.user
        ).filter(
            participants=target_user
        ).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, target_user)
        
        return redirect('conversation_detail', pk=conversation.pk)

class SendMessageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, participants=request.user)
        form = MessageForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']
            new_message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            conversation.save()
            
            context = {
                'message': new_message,
                'conversation': conversation,
                'message_form': MessageForm()  # Kirim form baru dalam response
            }
            return render(request, 'app/partials/_send_message_response.html', context)
        
        return HttpResponse(status=400)
    

class PollNewMessagesView(LoginRequiredMixin, View):
    """
    View ini akan dipanggil setiap beberapa detik oleh HTMX. Ia hanya akan mengembalikan pesan yang lebih baru dari ID pesan terakhir yang diketahui.
    """
    def get(self, request, pk):
        last_message_id = request.GET.get('last_message_id', 0)
        
        conversation = get_object_or_404(
            Conversation, 
            pk=pk, 
            participants=request.user
        )
        
        new_messages = conversation.messages.filter(
            id__gt=last_message_id
        ).order_by('timestamp')
        
        # Tentukan ID pesan terakhir yang baru untuk polling selanjutnya
        new_last_id = new_messages.last().id if new_messages else last_message_id
        
        context = {
            'messages': new_messages,
            'conversation': conversation,
            'new_last_message_id': new_last_id
        }
        
        return render(request, 'app/partials/_message_list_updates.html', context)
    

class UnreadCountView(LoginRequiredMixin, View):
    """
    View ini hanya akan menghitung dan merender badge notifikasi.
    Akan dipanggil oleh HTMX setiap beberapa detik.
    """
    def get(self, request):
        # Logika ini sama dengan yang ada di context processor Anda
        count = Message.objects.filter(
            conversation__participants=request.user, 
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        # Render hanya potongan HTML untuk badge notifikasi
        return render(request, 'app/partials/_dm_badge.html', {'unread_message_count': count})


# views.py
class NotificationUpdateView(LoginRequiredMixin, View):
    """
    Mengembalikan potongan HTML untuk badge, popup, dan pemicu polling baru.
    """
    def get(self, request):
        last_notification_id = request.GET.get('last_notification_id', 0)
        
        new_notifications = Notification.objects.filter(
            recipient=request.user,
            id__gt=last_notification_id
        ).order_by('id')

        unread_count = request.user.notifications.filter(is_read=False).count()
        
        # Tentukan ID notifikasi terakhir yang baru untuk polling selanjutnya
        new_last_id = new_notifications.last().id if new_notifications else last_notification_id
        
        context = {
            'unread_notification_count': unread_count,
            'new_notifications': new_notifications,
            'new_last_id': new_last_id
        }
        
        return render(request, 'app/partials/_notification_updates.html', context)
    

class NotificationListView(LoginRequiredMixin, ListView):
    """
    Menampilkan semua notifikasi untuk pengguna yang sedang login,
    dengan paginasi.
    """
    model = Notification
    template_name = 'app/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 15

    def get_queryset(self):
        # Ambil semua notifikasi untuk pengguna yang sedang login
        return self.request.user.notifications.all()


class MarkNotificationsAsReadView(LoginRequiredMixin, View):
    """
    View ini akan dipicu oleh HTMX saat ikon lonceng diklik.
    Ia akan menandai semua notifikasi yang belum dibaca sebagai "telah dibaca".
    """
    def post(self, request):
        # Tandai semua notifikasi yang belum dibaca milik pengguna sebagai "telah dibaca"
        request.user.notifications.filter(is_read=False).update(is_read=True)
        
        # Kirim kembali potongan HTML untuk badge (yang sekarang akan kosong)
        # Pastikan Anda memiliki file _notification_badge.html
        return render(request, 'app/partials/_notification_badge.html', {'unread_notification_count': 0})


class MarkAsReadAndRedirectView(LoginRequiredMixin, View):
    """
    Menandai satu notifikasi sebagai telah dibaca, lalu mengarahkan
    pengguna ke URL target dari notifikasi tersebut.
    """
    def get(self, request, notification_pk):
        # Dapatkan notifikasi, pastikan itu milik pengguna yang login
        notification = get_object_or_404(
            Notification, 
            pk=notification_pk, 
            recipient=request.user
        )
        
        # Tandai sebagai telah dibaca jika belum
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        
        # Dapatkan URL tujuan dari metode di model
        target_url = notification.get_absolute_url()
        
        # Fallback jika tidak ada URL target
        if not target_url or target_url == "#":
            return redirect('notification_list')
            
        return redirect(target_url)
    

class LoadNotificationDropdownView(LoginRequiredMixin, View):
    """
    View ini hanya akan mengambil notifikasi terbaru untuk ditampilkan
    di dalam dropdown, tanpa mengubah status is_read.
    """
    def get(self, request):
        # Ambil 5 notifikasi terbaru untuk pengguna yang login
        latest_notifications = request.user.notifications.all()[:5]
        
        # Render hanya potongan HTML yang berisi konten dropdown
        return render(
            request, 
            'app/partials/_notification_dropdown_content.html', 
            {'latest_notifications': latest_notifications}
        )


class UserSearchAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse([], safe=False)

        users = UserProfile.objects.filter(username__istartswith=query).exclude(pk=request.user.pk)[:10]
        
        results = [
            {
                'id': user.username,
                'text': user.username,
                'avatar': user.avatar.url if user.avatar else None
            }
            for user in users
        ]
        return JsonResponse(results, safe=False)
    

class CreateReportView(LoginRequiredMixin, View):
    def get(self, request, model_name, pk):
        """Menampilkan modal formulir laporan."""
        try:
            model = ContentType.objects.get(model=model_name).model_class()
            content_object = get_object_or_404(model, pk=pk)
            form = ReportForm()
            
            context = {
                'form': form,
                'content_object': content_object,
                'model_name': model_name,
                'pk': pk
            }
            return render(request, 'app/partials/_report_modal.html', context)
        except (ContentType.DoesNotExist, model.DoesNotExist):
            return HttpResponse("Invalid content type or object.", status=404)

    def post(self, request, model_name, pk):
        """Memproses pengiriman formulir laporan."""
        try:
            model = ContentType.objects.get(model=model_name).model_class()
            content_object = get_object_or_404(model, pk=pk)
            form = ReportForm(request.POST)

            if form.is_valid():
                report = form.save(commit=False)
                report.reporter = request.user
                report.content_object = content_object
                report.save()
                return render(request, 'app/partials/_report_success.html')
            
            # Jika form tidak valid, tampilkan kembali modal dengan error
            context = {
                'form': form,
                'content_object': content_object,
                'model_name': model_name,
                'pk': pk
            }
            return render(request, 'app/partials/_report_modal.html', context)
        except (ContentType.DoesNotExist, model.DoesNotExist):
            return HttpResponse("Invalid content type or object.", status=404)
        

class StaffRequiredMixin(AccessMixin):
    """Memastikan pengguna yang login adalah anggota staf."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

# === VIEW UNTUK HALAMAN ADMIN KUSTOM ===

class AdminDashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'management/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = UserProfile.objects.count()
        context['total_posts'] = Post.objects.count()
        context['total_comments'] = Comment.objects.count()
        context['pending_reports'] = Report.objects.filter(status=Report.ReportStatus.PENDING).count()
        context['recent_reports'] = Report.objects.order_by('-created_at')[:5]
        return context

class ReportListView(StaffRequiredMixin, ListView):
    model = Report
    template_name = 'management/report_list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        queryset = Report.objects.select_related('reporter', 'content_type').order_by('-created_at')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Report.ReportStatus.choices
        return context

class UpdateReportStatusView(StaffRequiredMixin, View):
    """Menangani pembaruan status laporan melalui HTMX."""
    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        new_status = request.POST.get('status')
        if new_status in Report.ReportStatus.values:
            report.status = new_status
            report.save(update_fields=['status'])
        
        # Kembalikan hanya bagian tombol aksi yang diperbarui
        return render(request, 'management/partials/_report_actions.html', {'report': report})

class AdminDeleteContentView(StaffRequiredMixin, View):
    """Menangani penghapusan konten yang dilaporkan."""
    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        content_object = report.content_object
        
        if content_object:
            content_object.delete()
            report.status = Report.ReportStatus.REVIEWED_ACTION_TAKEN
            report.save(update_fields=['status'])
        
        # Kembalikan seluruh KARTU yang diperbarui
        return render(request, 'management/partials/_report_card.html', {'report': report})
    

class UserListView(StaffRequiredMixin, ListView):
    model = UserProfile
    template_name = 'management/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    # === TAMBAHKAN METODE INI UNTUK MENANGANI HTMX ===
    def get_template_names(self):
        if self.request.htmx:
            return ['management/partials/_user_list_body.html']
        return [self.template_name]

    def get_queryset(self):
        queryset = UserProfile.objects.annotate(
            post_count=Count('posts')
        ).order_by('-date_joined')
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) | Q(email__icontains=query)
            )
        return queryset

class UpdateUserStatusView(StaffRequiredMixin, View):
    """Menangani pembaruan status is_active dan is_staff untuk pengguna."""
    def post(self, request, pk):
        user = get_object_or_404(UserProfile, pk=pk)
        
        # Jangan izinkan admin menonaktifkan dirinya sendiri
        if user == request.user:
            # Anda bisa menambahkan pesan error di sini jika mau
            return render(request, 'management/partials/_user_row.html', {'user': user})

        action = request.POST.get('action')
        
        if action == 'toggle_active':
            user.is_active = not user.is_active
        elif action == 'toggle_staff':
            user.is_staff = not user.is_staff
        
        user.save()
        
        # Render ulang baris pengguna dengan status terbaru
        return render(request, 'management/partials/_user_row.html', {'user': user})
    

# --- Game Management ---
class AdminGameListView(StaffRequiredMixin, ListView):
    model = Game
    template_name = 'management/game_list.html'
    context_object_name = 'games'
    paginate_by = 10

    def get_queryset(self):
        return Game.objects.all().order_by('title')

class AdminGameCreateView(StaffRequiredMixin, View):
    def get(self, request):
        form = AdminGameForm()
        return render(request, 'management/partials/_game_form.html', {'form': form})

    def post(self, request):
        form = AdminGameForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            games = Game.objects.all().order_by('-pk')
            response = render(request, 'management/partials/_game_list_body.html', {'games': games})
            response['HX-Trigger'] = 'close-modal'  # Kirim trigger untuk menutup modal
            return response
        return render(request, 'management/partials/_game_form.html', {'form': form})

class AdminGameUpdateView(StaffRequiredMixin, View):
    def get(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        form = AdminGameForm(instance=game)
        return render(request, 'management/partials/_game_form.html', {'form': form, 'game': game})

    def post(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        form = AdminGameForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            response = render(request, 'management/partials/_game_row.html', {'game': game})
            response['HX-Trigger'] = 'close-modal'  # Kirim trigger untuk menutup modal
            return response
        return render(request, 'management/partials/_game_form.html', {'form': form, 'game': game})

class AdminGameDeleteView(StaffRequiredMixin, View):
    def get(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        return render(request, 'management/partials/_game_confirm_delete.html', {
            'item': game,
            'delete_url': reverse('admin_game_delete', kwargs={'pk': pk})
        })

    def post(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        game.delete()
        response = HttpResponse()
        response['HX-Refresh'] = 'true'
        return response

# --- Category Management ---
class AdminCategoryListView(StaffRequiredMixin, ListView):
    model = PostCategory
    template_name = 'management/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        return PostCategory.objects.all().order_by('name')

class AdminCategoryCreateView(StaffRequiredMixin, View):
    def get(self, request):
        form = AdminCategoryForm()
        return render(request, 'management/partials/_category_form.html', {'form': form})

    def post(self, request):
        form = AdminCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            categories = PostCategory.objects.all().order_by('-pk')
            response = render(request, 'management/partials/_category_list_body.html', {'categories': categories})
            response['HX-Trigger'] = 'close-modal'  # Kirim trigger untuk menutup modal
            return response
        return render(request, 'management/partials/_category_form.html', {'form': form})

class AdminCategoryUpdateView(StaffRequiredMixin, View):
    def get(self, request, pk):
        category = get_object_or_404(PostCategory, pk=pk)
        form = AdminCategoryForm(instance=category)
        return render(request, 'management/partials/_category_form.html', {'form': form, 'category': category})

    def post(self, request, pk):
        category = get_object_or_404(PostCategory, pk=pk)
        form = AdminCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            response = render(request, 'management/partials/_category_row.html', {'category': category})
            response['HX-Trigger'] = 'close-modal'  # Kirim trigger untuk menutup modal
            return response
        return render(request, 'management/partials/_category_form.html', {'form': form, 'category': category})

class AdminCategoryDeleteView(StaffRequiredMixin, View):
    def get(self, request, pk):
        category = get_object_or_404(PostCategory, pk=pk)
        return render(request, 'management/partials/_category_confirm_delete.html', {
            'item': category,
            'delete_url': reverse('admin_category_delete', kwargs={'pk': pk})
        })

    def post(self, request, pk):
        category = get_object_or_404(PostCategory, pk=pk)
        category.delete()
        response = HttpResponse()
        response['HX-Refresh'] = 'true'  # Ini yang akan memicu refresh
        return response


class AdminAnalyticsView(StaffRequiredMixin, TemplateView):
    template_name = 'management/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # --- Data untuk 30 hari terakhir ---
        thirty_days_ago = timezone.now() - timedelta(days=30)
        date_labels = [(thirty_days_ago + timedelta(days=i)).strftime('%b %d') for i in range(31)]

        # 1. Pertumbuhan Pengguna
        user_registrations = (
            UserProfile.objects
            .filter(date_joined__gte=thirty_days_ago)
            .annotate(day=TruncDay('date_joined'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        
        user_data = {item['day'].strftime('%b %d'): item['count'] for item in user_registrations}
        user_growth_data = [user_data.get(day, 0) for day in date_labels]

        # 2. Aktivitas Konten
        post_creations = (
            Post.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        comment_creations = (
            Comment.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        post_data = {item['day'].strftime('%b %d'): item['count'] for item in post_creations}
        comment_data = {item['day'].strftime('%b %d'): item['count'] for item in comment_creations}
        
        post_activity_data = [post_data.get(day, 0) for day in date_labels]
        comment_activity_data = [comment_data.get(day, 0) for day in date_labels]

        # 3. Papan Peringkat
        context['top_users_by_karma'] = UserProfile.objects.order_by('-karma')[:5]
        context['top_posts_by_votes'] = Post.objects.annotate(score=Sum('votes__value')).filter(score__gt=0).order_by('-score')[:5]

        # Kirim data ke template dalam format JSON
        context['chart_labels'] = json.dumps(date_labels)
        context['user_growth_data'] = json.dumps(user_growth_data)
        context['post_activity_data'] = json.dumps(post_activity_data)
        context['comment_activity_data'] = json.dumps(comment_activity_data)
        
        return context
    
    
class OnboardingView(LoginRequiredMixin, View):
    def get(self, request):
        # Ambil beberapa game dan kategori populer untuk disarankan
        popular_games = Game.objects.annotate(num_posts=Count('posts')).order_by('-num_posts')[:12]
        all_categories = PostCategory.objects.all()
        
        context = {
            'games': popular_games,
            'categories': all_categories
        }
        return render(request, 'app/onboarding.html', context)

    def post(self, request):
        user = request.user
        selected_game_ids = request.POST.getlist('games')
        selected_category_ids = request.POST.getlist('categories')

        # Tambahkan game yang dipilih ke daftar following pengguna
        if selected_game_ids:
            games_to_follow = Game.objects.filter(pk__in=selected_game_ids)
            user.following_games.add(*games_to_follow)

        # Tambahkan kategori yang dipilih ke daftar following pengguna
        if selected_category_ids:
            categories_to_follow = PostCategory.objects.filter(pk__in=selected_category_ids)
            user.following_categories.add(*categories_to_follow)
            
        return redirect('home')
    

class GlobalSearchView(TemplateView):
    template_name = 'app/search_results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        result_type = self.request.GET.get('type', 'posts')

        queryset = None
        if not query:
            # Jika tidak ada query, kembalikan queryset kosong
            if result_type == 'posts':
                queryset = Post.objects.none()
            elif result_type == 'users':
                queryset = UserProfile.objects.none()
            elif result_type == 'games':
                queryset = Game.objects.none()
        else:
            # Jalankan query berdasarkan tipe hasil
            if result_type == 'users':
                queryset = UserProfile.objects.filter(username__icontains=query).order_by('username')
            elif result_type == 'games':
                queryset = Game.objects.filter(title__icontains=query).order_by('title')
            else: # Default ke 'posts'
                queryset = Post.objects.filter(
                    Q(title__icontains=query) | Q(content__icontains=query)
                ).distinct().order_by('-created_at')

        # Paginasi manual
        paginator = Paginator(queryset, 10)  # 10 hasil per halaman
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['query'] = query
        context['result_type'] = result_type
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        
        # Atur nama variabel konteks yang benar untuk template
        context[result_type] = page_obj.object_list
        
        return context
    

class LandingPageView(TemplateView):
    template_name = 'landing_page.html'

    def dispatch(self, request, *args, **kwargs):
        # Jika pengguna sudah login, alihkan ke halaman utama
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ambil beberapa statistik untuk ditampilkan di landing page
        context['user_count'] = UserProfile.objects.count()
        context['post_count'] = Post.objects.count()
        context['game_count'] = Game.objects.count()
        return context