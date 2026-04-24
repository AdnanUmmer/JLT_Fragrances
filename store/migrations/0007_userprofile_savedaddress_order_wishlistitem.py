from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0006_product_occasion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone_number", models.CharField(blank=True, max_length=25)),
                ("receive_offers", models.BooleanField(default=False)),
                ("google_account", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SavedAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("phone_number", models.CharField(max_length=25)),
                ("address_line", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("pincode", models.CharField(max_length=20)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_addresses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-is_default", "-created_at")},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("full_name", models.CharField(max_length=150)),
                ("phone_number", models.CharField(max_length=25)),
                ("address_line", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("pincode", models.CharField(max_length=20)),
                ("payment_method", models.CharField(choices=[("Cash on Delivery", "Cash on Delivery"), ("UPI Payment", "UPI Payment"), ("Razorpay", "Razorpay")], max_length=40)),
                ("status", models.CharField(choices=[("Processing", "Processing"), ("Confirmed", "Confirmed"), ("Shipped", "Shipped"), ("Delivered", "Delivered")], default="Processing", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="store.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to=settings.AUTH_USER_MODEL)),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="orders", to="store.variant")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="WishlistItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlisted_by", to="store.product")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlist_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",), "unique_together": {("user", "product")}},
        ),
    ]
