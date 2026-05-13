from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm, UserCreationForm as BaseUserCreationForm

from unfold.admin import ModelAdmin

from .models import RefreshToken, User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('email', 'name')


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(ModelAdmin,BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('email', 'name', 'role', 'is_onboarded', 'is_active', 'is_staff')
    list_filter = ('role', 'is_onboarded', 'is_active', 'is_staff')
    search_fields = ('email', 'name')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'country', 'initial_level')}),
        ('Role & Status', {'fields': ('role', 'is_onboarded', 'is_active', 'is_staff')}),
        ('Stats', {'fields': ('xp', 'streak', 'last_active')}),
        ('Permissions', {'fields': ('is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(RefreshToken)
class RefreshTokenAdmin(ModelAdmin):
    list_display = ('user', 'is_revoked', 'expires_at', 'created_at')
    list_filter = ('is_revoked',)
    readonly_fields = ('created_at',)
