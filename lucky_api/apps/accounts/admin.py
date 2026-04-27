from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import CustomUser


# Register your models here.
@admin.register(CustomUser)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-id"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "other",
            {
                "fields": ("wallet_address", "member_type"),
            },
        ),
    )
