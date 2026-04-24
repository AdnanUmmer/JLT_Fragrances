from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0007_userprofile_savedaddress_order_wishlistitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedaddress",
            name="address_line_2",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="savedaddress",
            name="country",
            field=models.CharField(default="India", max_length=100),
        ),
        migrations.AddField(
            model_name="savedaddress",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="savedaddress",
            name="landmark",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="savedaddress",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="address_line_2",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="country",
            field=models.CharField(default="India", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="order",
            name="landmark",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_fee",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_method",
            field=models.CharField(choices=[("Standard", "Standard"), ("Express", "Express")], default="Standard", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="total_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="order",
            name="payment_method",
            field=models.CharField(choices=[("Cash on Delivery", "Cash on Delivery"), ("UPI", "UPI"), ("Card", "Card"), ("Net Banking", "Net Banking"), ("Wallets", "Wallets"), ("Razorpay", "Razorpay")], max_length=40),
        ),
    ]
