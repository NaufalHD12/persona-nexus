from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from .models import Post, Game, Vote, PostCategory, Comment, UserProfile, Conversation, Message
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView, TemplateView
from django.db.models.query import QuerySet
from django.db.models import OuterRef, Subquery, Count, Q, Sum
from .forms import CommentForm, PostForm, MessageForm
from django.urls import reverse_lazy
from friendship.models import Follow
from django.contrib import messages
from django import forms


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10

    def get_template_names(self):
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return ["app/home.html"]

    def get_queryset(self):
        # ==> PERBAIKAN 1: Anotasi skor vote di awal <==
        queryset = super().get_queryset().annotate(
            score=Sum('votes__value', default=0) # Hitung skor dan beri nama 'score'
        )

        sort_by = self.request.GET.get('sort', 'new')
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(content__icontains=query))

        # ==> PERBAIKAN 2: Gunakan 'score' untuk mengurutkan, bukan 'vote_score' <==
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
        context['featured_games'] = Game.objects.all()[:3]
        context['popular_categories'] = PostCategory.objects.annotate(num_posts=Count('posts')).order_by('-num_posts')[:4]
        return context

    

class FollowingPostListView(LoginRequiredMixin, ListView):
    model = Post
    context_object_name = "posts"
    paginate_by = 10

    def get_template_names(self):
        """
        Mengembalikan template parsial jika request berasal dari HTMX.
        """
        if self.request.htmx:
            return ["app/partials/_post_list.html"]
        return ["app/following.html"]

    def get_queryset(self):
        following_users = Follow.objects.following(self.request.user)
        if not following_users:
            return Post.objects.none()

        queryset = Post.objects.filter(author__in=following_users).annotate(
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
        """
        Menyediakan context untuk sidebar.
        """
        context = super().get_context_data(**kwargs)
        context['featured_games'] = Game.objects.all()[:3]
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
        # Tambahkan anotasi vote ke objek post utama
        post = context['post']
        if self.request.user.is_authenticated:
            user_vote = post.votes.filter(user=self.request.user).first()
            post.user_vote_value = user_vote.value if user_vote else None
            
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
    
    
class CategoryListView(ListView):
    template_name = 'app/categories.html'
    model = PostCategory
    context_object_name = 'categories'    
    

class VoteView(LoginRequiredMixin, View):
    
    def post(self, request, model_name, pk, direction):
        # 1. Dapatkan model dan objek yang akan di-vote
        try:
            model = ContentType.objects.get(model=model_name).model_class()
        except ContentType.DoesNotExist:
            return JsonResponse({'error': 'Invalid model name'}, status=400)
        
        content_object = get_object_or_404(model, pk=pk)
        
        # 2. Tentukan nilai vote yang diinginkan
        vote_value = Vote.UPVOTE if direction == 'up' else Vote.DOWNVOTE

        # 3. Coba dapatkan vote yang sudah ada dari pengguna untuk objek ini
        try:
            vote = Vote.objects.get(
                user=request.user,
                content_type=ContentType.objects.get_for_model(content_object),
                object_id=content_object.id
            )
            
            # **LOGIKA BARU:**
            # Jika pengguna menekan tombol yang sama, batalkan vote.
            if vote.value == vote_value:
                vote.delete()
                user_vote_status = 'none'
            # Jika pengguna menekan tombol yang BERLAWANAN, batalkan juga vote yang lama.
            else:
                vote.delete()
                user_vote_status = 'none'

        # Jika belum ada vote, buat yang baru.
        except Vote.DoesNotExist:
            Vote.objects.create(
                user=request.user,
                content_object=content_object,
                value=vote_value
            )
            user_vote_status = 'up' if vote_value == Vote.UPVOTE else 'down'

        # 4. Kembalikan skor baru dan status vote pengguna
        return JsonResponse({
            'success': True,
            'score': content_object.vote_score,
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
    context_object_name = 'profile_user' # Nama variabel untuk pengguna di template
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        
        context['posts'] = profile_user.posts.all().order_by('-created_at')

        if self.request.user == profile_user:
            context['saved_posts'] = profile_user.saved_posts.all().order_by('-created_at')
        context['followers_count'] = len(Follow.objects.followers(profile_user))
        context['following_count'] = len(Follow.objects.following(profile_user))
        
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
        # Selalu sediakan daftar percakapan untuk sidebar kiri
        context['conversations'] = self.request.user.conversations.all().order_by('-updated_at')
        
        # Jika ada 'pk' di URL, berarti kita ingin menampilkan percakapan spesifik
        if 'pk' in kwargs:
            conversation = get_object_or_404(
                Conversation, 
                pk=kwargs['pk'], 
                participants=self.request.user
            )
            context['conversation'] = conversation
            context['message_form'] = MessageForm()
        
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
    """
    View kecil ini HANYA untuk menangani pengiriman pesan (POST).
    """
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, participants=request.user)
        form = MessageForm(request.POST)
        if form.is_valid():
            # ==> PERBAIKAN: Ambil data dari form dan buat objek secara manual <==
            content = form.cleaned_data['content']
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            conversation.save() # Update timestamp
            
            # Kembalikan hanya gelembung pesan baru untuk HTMX
            return render(request, 'app/partials/_message_bubble.html', {'message': message})
        return HttpResponse(status=400)