from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from app.models import Report, UserProfile, PostCategory, Game, Post, Comment, Vote

# Mendaftarkan model UserProfile kustom Anda
# Kita mewarisi dari UserAdmin untuk mendapatkan semua fungsionalitas admin user bawaan
class UserProfileAdmin(UserAdmin):
    # Menambahkan field 'bio' dan 'avatar' ke dalam tampilan admin
    # `fieldsets` digunakan untuk mengelompokkan field di halaman edit admin
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Profile Info', {'fields': ('bio', 'avatar')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Profile Info', {'fields': ('bio', 'avatar')}),
    )

# Mendaftarkan model Post dengan tampilan yang lebih informatif
class PostAdmin(admin.ModelAdmin):
    # Menampilkan kolom ini di daftar postingan
    list_display = ('title', 'author', 'game_title', 'category', 'created_at')
    # Menambahkan filter di sidebar kanan
    list_filter = ('game_title', 'category', 'created_at')
    # Menambahkan field pencarian
    search_fields = ('title', 'content')
    # Mengisi field 'slug' secara otomatis (jika ada) dari 'title'
    # prepopulated_fields = {'slug': ('title',)}

# Mendaftarkan model Comment dengan tampilan yang lebih baik
class CommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'author', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content',)

# Mendaftarkan model Game
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)} # Otomatis isi slug dari title
    

# === Daftarkan semua model Anda di sini ===
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PostCategory)
admin.site.register(Game, GameAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Vote)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'content_object', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    readonly_fields = ('reporter', 'content_object', 'reason', 'notes', 'created_at')
    list_editable = ('status',)