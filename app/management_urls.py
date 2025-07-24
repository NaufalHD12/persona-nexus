from django.urls import path
from .views import (
    AdminAnalyticsView,
    AdminDashboardView, 
    ReportListView, 
    UpdateReportStatusView,
    AdminDeleteContentView,
    UserListView,
    UpdateUserStatusView,
    # --- Impor view baru ---
    AdminGameListView,
    AdminGameCreateView,
    AdminGameUpdateView,
    AdminGameDeleteView,
    AdminCategoryListView,
    AdminCategoryCreateView,
    AdminCategoryUpdateView,
    AdminCategoryDeleteView,
)

urlpatterns = [
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Reports
    path('reports/', ReportListView.as_view(), name='admin_report_list'),
    path('reports/<int:pk>/update_status/', UpdateReportStatusView.as_view(), name='admin_update_report_status'),
    path('reports/<int:pk>/delete_content/', AdminDeleteContentView.as_view(), name='admin_delete_content'),
    
    # Users
    path('users/', UserListView.as_view(), name='admin_user_list'),
    path('users/<int:pk>/update_status/', UpdateUserStatusView.as_view(), name='admin_update_user_status'),

    # Games
    path('games/', AdminGameListView.as_view(), name='admin_game_list'),
    path('games/create/', AdminGameCreateView.as_view(), name='admin_game_create'),
    path('games/<int:pk>/update/', AdminGameUpdateView.as_view(), name='admin_game_update'),
    path('games/<int:pk>/delete/', AdminGameDeleteView.as_view(), name='admin_game_delete'),

    # Categories
    path('categories/', AdminCategoryListView.as_view(), name='admin_category_list'),
    path('categories/create/', AdminCategoryCreateView.as_view(), name='admin_category_create'),
    path('categories/<int:pk>/update/', AdminCategoryUpdateView.as_view(), name='admin_category_update'),
    path('categories/<int:pk>/delete/', AdminCategoryDeleteView.as_view(), name='admin_category_delete'),
    
    path('analytics/', AdminAnalyticsView.as_view(), name='admin_analytics'),
]
