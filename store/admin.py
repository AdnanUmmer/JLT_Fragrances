from django.contrib import admin
from .models import (
    CollectionCard,
    Order,
    Product,
    ProductImage,
    SavedAddress,
    UserProfile,
    Variant,
    WishlistItem,
)


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1



@admin.register(CollectionCard)
class CollectionCardAdmin(admin.ModelAdmin):
    list_display = ("title", "collection_type", "ordering", "is_active", "updated_at")
    list_filter = ("collection_type", "is_active")
    list_editable = ("ordering", "is_active")
    search_fields = ("title", "subtitle", "button_text", "destination_url")
    ordering = ("ordering", "id")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("inspired_by", "brand", "category")
    search_fields = ("inspired_by", "brand", "category")
    inlines = [VariantInline, ProductImageInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "receive_offers", "google_account")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "phone_number",
    )


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__email", "product__inspired_by")


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "city", "pincode", "is_default")
    search_fields = (
        "user__email",
        "full_name",
        "phone_number",
        "city",
        "pincode",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "product",
        "quantity",
        "price",
        "payment_method",
        "payment_status",
        "is_paid",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_method", "payment_status", "is_paid")
    search_fields = (
        "user__email",
        "product__inspired_by",
        "full_name",
        "phone_number",
        "razorpay_payment_id",
        "razorpay_order_id",
    )


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "price")
    search_fields = ("product__inspired_by", "size")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "sort_order", "created_at")
    search_fields = ("product__inspired_by", "alt_text")


