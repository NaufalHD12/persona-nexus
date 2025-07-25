from django.urls import path
from .views import (
    CreateReportView, GlobalSearchView, OnboardingView, PostListView, UserSearchAPIView, VoteView, GameListView, CategoryListView, PostDetailView, 
    AddCommentView, SettingsView, PostCreateView, ProfileDetailView, 
    FollowToggleView, FollowingPostListView, SavePostToggleView, 
    PostUpdateView, PostDeleteView, SuccessModalView, StartConversationView, 
    InboxView, SendMessageView, PollNewMessagesView, UnreadCountView,
    NotificationUpdateView, NotificationListView, MarkAsReadAndRedirectView, LoadNotificationDropdownView, GameDetailView,
    CategoryDetailView, ToggleGameFollowView, ToggleCategoryFollowView # <-- Impor view baru
)

urlpatterns = [
    path('welcome/onboarding/', OnboardingView.as_view(), name='onboarding'),
    path('search/', GlobalSearchView.as_view(), name='search_results'),
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
    path("games/<slug:slug>/", GameDetailView.as_view(), name="game_detail"), 
    path("games/<slug:slug>/toggle_follow/", ToggleGameFollowView.as_view(), name="toggle_follow_game"), # <-- BARIS INI DITAMBAHKAN

    path("categories/", CategoryListView.as_view(), name="categories"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category_detail"),
    path("categories/<slug:slug>/toggle_follow/", ToggleCategoryFollowView.as_view(), name="toggle_follow_category"), # <-- BARIS INI DITAMBAHKAN

    path('api/user-search/', UserSearchAPIView.as_view(), name='user_search_api'),

    path('report/<str:model_name>/<int:pk>/', CreateReportView.as_view(), name='create_report'),
    
    path('account/settings/', SettingsView.as_view(), name='account_settings'),
    
    path('profile/<str:username>/', ProfileDetailView.as_view(), name='profile_detail'),
    path('profile/<str:username>/toggle_follow/', FollowToggleView.as_view(), name="toggle_follow"),
    path('success-modal/', SuccessModalView.as_view(), name='success_modal'),
    path('messages/', InboxView.as_view(), name='message_inbox'),
    path('messages/<int:pk>/', InboxView.as_view(), name='conversation_detail'),
    path('messages/start/<str:username>/', StartConversationView.as_view(), name='start_conversation'),
    path('messages/<int:pk>/send/', SendMessageView.as_view(), name='send_message'),
    path('messages/<int:pk>/poll/', PollNewMessagesView.as_view(), name='poll_new_messages'),
    path('notifications/unread_count/', UnreadCountView.as_view(), name='unread_count'),
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/<int:notification_pk>/read/', MarkAsReadAndRedirectView.as_view(), name='mark_as_read_and_redirect'),
    path('notifications/update/', NotificationUpdateView.as_view(), name='notification_update'),
    path('notifications/load-dropdown/', LoadNotificationDropdownView.as_view(), name='load_notification_dropdown'),
]
