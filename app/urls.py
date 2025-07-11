from django.urls import path
from .views import PostListView, VoteView, GameListView, CategoryListView, PostDetailView, AddCommentView, SettingsView, PostCreateView, ProfileDetailView, FollowToggleView,  FollowingPostListView, SavePostToggleView, PostUpdateView, PostDeleteView, SuccessModalView, StartConversationView, InboxView, SendMessageView

urlpatterns = [
    path('post/create/', PostCreateView.as_view(), name='create_post'),
    path("", PostListView.as_view(), name="home"),
    path("following/", FollowingPostListView.as_view(), name="following_feed"),
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/comment/', AddCommentView.as_view(), name='add_comment'),
    path('post/<slug:slug>/toggle_save/', SavePostToggleView.as_view(), name='toggle_save'),
    path('post/<slug:slug>/update/', PostUpdateView.as_view(), name='post_update'),
    path('post/<slug:slug>/delete/', PostDeleteView.as_view(), name='post_delete'),
    path('vote/<str:model_name>/<int:pk>/<str:direction>/', VoteView.as_view(), name='vote'),
    path("games/", GameListView.as_view(), name="game_directory"),
    path("categories/", CategoryListView.as_view(), name="categories"),
    path('account/settings/', SettingsView.as_view(), name='account_settings'),
    path('profile/<str:username>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/<str:username>/toggle_follow/', FollowToggleView.as_view(), name="toggle_follow"),
    path('success-modal/', SuccessModalView.as_view(), name='success_modal'),
    path('messages/', InboxView.as_view(), name='message_inbox'),
    path('messages/<int:pk>/', InboxView.as_view(), name='conversation_detail'),
    path('messages/start/<str:username>/', StartConversationView.as_view(), name='start_conversation'),
    path('messages/<int:pk>/send/', SendMessageView.as_view(), name='send_message'),
]
