import json
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from email.utils import formataddr, parseaddr
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordResetView
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    CheckoutForm,
    LuxuryAuthenticationForm,
    NewsletterPreferencesForm,
    ProfileForm,
    SignupForm,
)
from .models import AboutSection, HeroSection, Order, Product, ProductImage, SavedAddress, Variant, WishlistItem

logger = logging.getLogger(__name__)
User = get_user_model()

STANDARD_SHIPPING_FEE = Decimal("0.00")
EXPRESS_SHIPPING_FEE = Decimal("249.00")
ADDRESS_FIELDS = (
    "full_name",
    "email",
    "phone_number",
    "address_line",
    "address_line_2",
    "city",
    "state",
    "country",
    "pincode",
    "landmark",
)

POLICY_PAGES = {
    "privacy": {
        "title": "Privacy Policy",
        "eyebrow": "Private Client Care",
        "intro": "Your details are handled with the same discretion, security, and refinement that define every JLT Fragrances experience.",
        "sections": [
            {
                "heading": "Information We Collect",
                "body": "We collect the details required to fulfil your order and support your account, including your name, email address, phone number, delivery address, and order history.",
            },
            {
                "heading": "How We Use It",
                "body": "Your information is used to process orders, arrange delivery, communicate updates, improve our storefront, and provide personalised service when you choose to hear from us.",
            },
            {
                "heading": "Security & Retention",
                "body": "We keep customer information on secure systems and retain only what is reasonably necessary for operations, compliance, support, and legitimate business records.",
            },
        ],
    },
    "refund": {
        "title": "Refund Policy",
        "eyebrow": "Order Assurance",
        "intro": "We package every fragrance with care. If an eligible prepaid order arrives damaged or incorrect, we review it promptly and resolve it with clarity.",
        "sections": [
            {
                "heading": "Eligible Cases",
                "body": "Refunds may be issued for prepaid orders that arrive damaged, defective, or materially different from what was ordered, subject to review of the request and supporting details.",
            },
            {
                "heading": "Request Window",
                "body": "Please contact us as soon as possible after delivery with your order number, a brief explanation, and photos when relevant so we can investigate without delay.",
            },
            {
                "heading": "Processing Timeline",
                "body": "Once approved, refunds are initiated to the original payment source. Banking timelines may vary depending on your provider and payment method.",
            },
        ],
    },
    "shipping": {
        "title": "Shipping Policy",
        "eyebrow": "Delivery Promise",
        "intro": "Every order is prepared for arrival with secure packaging, signature presentation, and delivery options designed around convenience and urgency.",
        "sections": [
            {
                "heading": "Standard Delivery",
                "body": "Standard shipping is complimentary and is ideal for most fragrance orders. Delivery timelines vary by destination and operational conditions.",
            },
            {
                "heading": "Express Delivery",
                "body": "Express shipping is prioritised for faster dispatch and is shown transparently at checkout. Any additional charge is added instantly before payment.",
            },
            {
                "heading": "Address Accuracy",
                "body": "Please ensure all delivery details are complete and accurate. Delays caused by incomplete addresses or unavailable recipients may affect delivery timelines.",
            },
        ],
    },
}

CONTACT_PAGE = {
    "title": "Contact Us",
    "eyebrow": "Concierge Support",
    "intro": "Questions about an order, fragrance guidance, or delivery? Our team is ready to help with timely, polished support.",
    "items": [
        {"label": "Email", "value": "support@jltfragrances.com"},
        {"label": "Phone", "value": "+91 98765 43210"},
        {"label": "Studio Hours", "value": "Monday to Saturday, 10:00 AM to 7:00 PM"},
        {"label": "Address", "value": "JLT Fragrances, Luxury Perfume Studio, India"},
    ],
}


def _get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None

    try:
        import razorpay
    except ImportError:
        logger.exception("Razorpay package is not installed.")
        return None

    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def get_wishlist_ids(request):
    if request.user.is_authenticated:
        return list(
            WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
        )
    return []


def _get_safe_redirect(request, default="home"):
    redirect_to = request.POST.get("next") or request.GET.get("next")
    if redirect_to and url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return reverse(default)


def _google_login_url(next_url):
    for name, args in (("google_login", []), ("socialaccount_login", ["google"])):
        try:
            url = reverse(name, args=args)
            return f"{url}?process=login&next={quote(next_url, safe='/?:=&')}"
        except NoReverseMatch:
            continue
    return None


def _redirect_to_login(request, next_url, message_text):
    messages.info(request, message_text)
    return redirect(f"{reverse('login')}?next={quote(next_url, safe='/?:=&')}")


def _shipping_fee(method):
    return EXPRESS_SHIPPING_FEE if method == "Express" else STANDARD_SHIPPING_FEE


def _delivery_text(method):
    target_date = timezone.localdate() + timedelta(days=3 if method == "Express" else 6)
    return f"Estimated delivery by {target_date.strftime('%d %b %Y')}"


def _parse_quantity(value):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def _format_money(value):
    return f"{Decimal(str(value)):.2f}"


def _product_image_url(product):
    if product:
        return product.image_url
    extra = product.extra_images.first() if product else None
    if extra:
        return extra.image_url
    return ""


def _gallery_images(product):
    images = []
    if product.image:
        images.append(
            {
                "url": product.image_url,
                "alt": product.inspired_by,
                "id": f"primary-{product.id}",
            }
        )

    for image in product.extra_images.all():
        if not image.image:
            continue
        images.append(
            {
                "url": image.image_url,
                "alt": image.alt_text or product.inspired_by,
                "id": f"gallery-{image.id}",
            }
        )

    if not images:
        images.append(
            {
                "url": product.image_url,
                "alt": product.inspired_by,
                "id": f"placeholder-{product.id}",
            }
        )

    return images


def _build_cart_items(cart):
    items = []
    subtotal = Decimal("0.00")

    for key, item in cart.items():
        line_total = Decimal(str(item["price"])) * int(item["quantity"])
        subtotal += line_total

        product_id = None
        variant_id = None
        if "_" in key:
            raw_product_id, raw_variant_id = key.split("_", 1)
            try:
                product_id = int(raw_product_id)
                variant_id = int(raw_variant_id)
            except ValueError:
                product_id = None
                variant_id = None

        items.append(
            {
                "id": key,
                "product_id": product_id,
                "variant_id": variant_id,
                "name": item["name"],
                "size": item.get("size"),
                "price": Decimal(str(item["price"])),
                "quantity": int(item["quantity"]),
                "image": item.get("image", ""),
                "total": line_total,
            }
        )

    return items, subtotal


def _single_checkout_item(product, variant, quantity):
    line_total = Decimal(str(variant.price)) * quantity
    return [
        {
            "id": f"{product.id}_{variant.id}",
            "product_id": product.id,
            "variant_id": variant.id,
            "product": product,
            "variant": variant,
            "name": product.inspired_by,
            "size": variant.size,
            "price": Decimal(str(variant.price)),
            "quantity": quantity,
            "image": _product_image_url(product),
            "total": line_total,
        }
    ], line_total


def _default_checkout_initial(user):
    initial = {
        "email": user.email,
        "country": "India",
        "payment_method": "Razorpay",
        "shipping_method": "Standard",
    }
    default_address = user.saved_addresses.filter(is_default=True).first()
    if default_address:
        initial.update(
            {
                "full_name": default_address.full_name,
                "email": default_address.email or user.email,
                "phone_number": default_address.phone_number,
                "address_line": default_address.address_line,
                "address_line_2": default_address.address_line_2,
                "city": default_address.city,
                "state": default_address.state,
                "country": default_address.country,
                "pincode": default_address.pincode,
                "landmark": default_address.landmark,
            }
        )
    elif hasattr(user, "profile"):
        initial.update(
            {
                "full_name": user.get_full_name(),
                "phone_number": user.profile.phone_number,
            }
        )
    return initial


def _serialize_address(cleaned_data):
    return {field: cleaned_data.get(field, "") for field in ADDRESS_FIELDS}


def _build_checkout_context(request, *, form, checkout_mode, checkout_items, subtotal, shipping_method, shipping_fee, total_price, product=None, variant=None, quantity=None):
    return {
        "checkout_mode": checkout_mode,
        "checkout_items": checkout_items,
        "product": product,
        "variant": variant,
        "quantity": quantity,
        "form": form,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "total_price": total_price,
        "delivery_text": _delivery_text(shipping_method),
        "wishlist_items": get_wishlist_ids(request),
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "brand_logo_url": settings.BRAND_LOGO_URL,
    }


def _serialize_pending_item(item):
    return {
        "product_id": item["product_id"],
        "variant_id": item["variant_id"],
        "name": item["name"],
        "size": item["size"],
        "price": _format_money(item["price"]),
        "quantity": int(item["quantity"]),
        "image": item.get("image", ""),
        "total": _format_money(item["total"]),
    }


def _build_notification_message(orders):
    first_order = orders[0]
    item_lines = []
    for order in orders:
        product_name = order.product.inspired_by if order.product else "Fragrance Order"
        size = f" ({order.variant.size})" if order.variant else ""
        item_lines.append(f"- {product_name}{size} x {order.quantity} = Rs. {order.total_amount}")

    address_bits = [
        first_order.address_line,
        first_order.address_line_2,
        first_order.landmark,
        first_order.city,
        first_order.state,
        first_order.country,
        first_order.pincode,
    ]
    address = ", ".join(bit for bit in address_bits if bit)
    total_amount = sum(order.total_amount for order in orders)

    return (
        f"New JLT Fragrances order received.\n"
        f"Order IDs: {', '.join(str(order.id) for order in orders)}\n"
        f"Customer: {first_order.full_name}\n"
        f"Phone: {first_order.phone_number}\n"
        f"Email: {first_order.email or 'N/A'}\n"
        f"Payment: {first_order.payment_method}\n"
        f"Shipping: {first_order.shipping_method}\n"
        f"Total: Rs. {total_amount}\n"
        f"Address: {address}\n"
        f"Items:\n" + "\n".join(item_lines)
    )


def _notification_from_email():
    configured_from = (settings.DEFAULT_FROM_EMAIL or "").strip()
    display_name, parsed_email = parseaddr(configured_from)
    smtp_user = (settings.EMAIL_HOST_USER or "").strip()
    email_host = (settings.EMAIL_HOST or "").strip().lower()

    fallback_email = parsed_email or smtp_user or configured_from
    if not fallback_email:
        return ""

    if "gmail" in email_host and smtp_user and fallback_email.lower() != smtp_user.lower():
        safe_sender = formataddr((display_name or "JLT Fragrances", smtp_user))
        logger.warning(
            "DEFAULT_FROM_EMAIL %r does not match Gmail SMTP user %r. Using the authenticated sender instead.",
            configured_from,
            smtp_user,
        )
        return safe_sender

    return formataddr((display_name, fallback_email)) if display_name else fallback_email


def _send_owner_email_notification(subject, message_body, order_ids):
    if not settings.OWNER_NOTIFICATION_EMAIL:
        logger.info(
            "Owner email notification skipped for orders %s because OWNER_NOTIFICATION_EMAIL is not configured.",
            order_ids,
        )
        return False

    from_email = _notification_from_email() or settings.DEFAULT_FROM_EMAIL

    try:
        email = EmailMessage(
            subject=subject,
            body=message_body,
            from_email=from_email,
            to=[settings.OWNER_NOTIFICATION_EMAIL],
        )
        sent_count = email.send(fail_silently=False)
        if sent_count:
            logger.info(
                "Owner email sent successfully for orders %s to %s.",
                order_ids,
                settings.OWNER_NOTIFICATION_EMAIL,
            )
            return True

        logger.error("Owner email backend reported no messages sent for orders %s.", order_ids)
    except Exception as exc:
        logger.exception("Owner email notification failed for orders %s: %s", order_ids, exc)

    return False


def _send_telegram_notification(message_body, order_ids):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False

    try:
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message_body,
            }
        ).encode("utf-8")
        request = Request(
            telegram_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            response.read()
        logger.info("Telegram notification sent successfully for orders %s.", order_ids)
        return True
    except Exception:
        logger.exception("Telegram notification failed for orders %s", order_ids)
        return False


def _send_owner_notifications(orders):
    if not orders:
        return

    order_ids = [order.id for order in orders]
    message_body = _build_notification_message(orders)
    subject = f"New JLT Fragrances Order #{orders[0].id}"

    _send_owner_email_notification(subject, message_body, order_ids)
    _send_telegram_notification(message_body, order_ids)


def _is_custom_admin(user):
    return user.is_active and user.is_superuser


def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user and user.is_superuser:
            login(request, user)
            return redirect("admin_dashboard")

        messages.error(request, "Only superuser accounts can access the admin panel.")

    return render(request, "custom_admin/login.html")


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_dashboard(request):
    revenue = Order.objects.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

    return render(
        request,
        "admin/dashboard.html",
        {
            "total_orders": Order.objects.count(),
            "total_users": User.objects.count(),
            "total_revenue": revenue,
        },
    )


def _get_sort(request, allowed, default):
    requested = request.GET.get("sort", default)
    return requested if requested in allowed else default


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_orders(request):
    allowed_sorts = {
        "user": "full_name",
        "-user": "-full_name",
        "email": "email",
        "-email": "-email",
        "total": "total_amount",
        "-total": "-total_amount",
        "payment": "payment_status",
        "-payment": "-payment_status",
        "date": "created_at",
        "-date": "-created_at",
    }
    sort = _get_sort(request, allowed_sorts, "-date")
    orders = Order.objects.select_related("user", "product", "variant")
    search_query = request.GET.get("q", "").strip()
    payment_status = request.GET.get("payment_status", "").strip()
    order_status = request.GET.get("status", "").strip()

    if search_query:
        orders = orders.filter(
            Q(full_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone_number__icontains=search_query)
            | Q(product__inspired_by__icontains=search_query)
            | Q(razorpay_payment_id__icontains=search_query)
            | Q(razorpay_order_id__icontains=search_query)
        )
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if order_status:
        orders = orders.filter(status=order_status)

    orders = orders.order_by(allowed_sorts[sort])
    return render(
        request,
        "admin/orders.html",
        {
            "orders": orders,
            "current_sort": sort,
            "search_query": search_query,
            "payment_status": payment_status,
            "order_status": order_status,
            "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
            "order_status_choices": Order.STATUS_CHOICES,
        },
    )


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user", "product", "variant"),
        id=order_id,
    )
    return render(request, "admin/order_detail.html", {"order": order})


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_users(request):
    allowed_sorts = {
        "name": "first_name",
        "-name": "-first_name",
        "email": "email",
        "-email": "-email",
        "date": "date_joined",
        "-date": "-date_joined",
    }
    sort = _get_sort(request, allowed_sorts, "-date")
    users = User.objects.prefetch_related("saved_addresses").select_related("profile")
    search_query = request.GET.get("q", "").strip()
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(profile__phone_number__icontains=search_query)
        )
    users = users.order_by(allowed_sorts[sort])
    user_rows = []

    for user in users:
        address = user.saved_addresses.first()
        try:
            profile_phone = user.profile.phone_number
        except ObjectDoesNotExist:
            profile_phone = ""

        address_text = "N/A"
        if address:
            address_text = ", ".join(
                part
                for part in (
                    address.address_line,
                    address.city,
                    address.state,
                    address.pincode,
                )
                if part
            )

        user_rows.append(
            {
                "name": user.get_full_name() or user.username,
                "email": user.email or "N/A",
                "phone": profile_phone or (address.phone_number if address else "") or "N/A",
                "address": address_text,
                "edit_url": reverse("admin_user_edit", args=[user.id]),
            }
        )

    return render(
        request,
        "admin/users.html",
        {"users": user_rows, "current_sort": sort, "search_query": search_query},
    )


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    try:
        profile = user.profile
    except ObjectDoesNotExist:
        profile = None

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.email = request.POST.get("email", "").strip()
        user.username = request.POST.get("username", "").strip() or user.email or user.username
        user.is_active = request.POST.get("is_active") == "on"
        user.save(update_fields=["first_name", "last_name", "email", "username", "is_active"])

        if profile:
            profile.phone_number = request.POST.get("phone_number", "").strip()
            profile.receive_offers = request.POST.get("receive_offers") == "on"
            profile.save(update_fields=["phone_number", "receive_offers"])

        messages.success(request, "User updated.")
        return redirect("admin_users")

    return render(request, "admin/user_form.html", {"edited_user": user, "profile": profile})


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_products(request):
    allowed_sorts = {
        "name": "inspired_by",
        "-name": "-inspired_by",
        "brand": "brand",
        "-brand": "-brand",
        "category": "category",
        "-category": "-category",
        "bestseller": "-is_bestseller",
        "-bestseller": "is_bestseller",
    }
    sort = _get_sort(request, allowed_sorts, "name")
    products = Product.objects.prefetch_related("variants")
    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    bestseller = request.GET.get("bestseller", "").strip()

    if search_query:
        products = products.filter(
            Q(inspired_by__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
        )
    if category:
        products = products.filter(category=category)
    if bestseller in {"yes", "no"}:
        products = products.filter(is_bestseller=(bestseller == "yes"))

    categories = Product.objects.order_by("category").values_list("category", flat=True).distinct()
    products = products.order_by(allowed_sorts[sort])
    return render(
        request,
        "admin/products.html",
        {
            "products": products,
            "current_sort": sort,
            "search_query": search_query,
            "category": category,
            "bestseller": bestseller,
            "categories": categories,
        },
    )


def _parse_admin_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _save_product_from_admin_request(request, product=None):
    product = product or Product()
    is_new_product = product.pk is None
    product.inspired_by = request.POST.get("inspired_by", "").strip()
    product.brand = request.POST.get("brand", "").strip()
    product.category = request.POST.get("category", "").strip()
    product.description = request.POST.get("description", "").strip()
    product.top_note = request.POST.get("top_note", "").strip()
    product.middle_note = request.POST.get("middle_note", "").strip()
    product.base_note = request.POST.get("base_note", "").strip()
    product.occasion = request.POST.get("occasion", "").strip()
    product.stock = max(0, _parse_admin_int(request.POST.get("stock"), 0))
    product.is_bestseller = request.POST.get("is_bestseller") == "on"

    primary_image = request.FILES.get("image")
    if primary_image:
        product.image = primary_image
    product.save()

    seen_variant_ids = set()
    submitted_valid_variants = False
    variant_ids = request.POST.getlist("variant_id")
    sizes = request.POST.getlist("variant_size")
    prices = request.POST.getlist("variant_price")
    delete_variant_ids = set(request.POST.getlist("delete_variant"))

    for index, size in enumerate(sizes):
        size = size.strip()
        price = _parse_admin_int(prices[index] if index < len(prices) else None, 0)
        variant_id = variant_ids[index] if index < len(variant_ids) else ""
        if variant_id in delete_variant_ids:
            continue
        if not size or price <= 0:
            continue

        variant = product.variants.filter(id=variant_id).first() if variant_id else Variant(product=product)
        variant.size = size
        variant.price = price
        variant.save()
        seen_variant_ids.add(variant.id)
        submitted_valid_variants = True

    if delete_variant_ids:
        product.variants.filter(id__in=delete_variant_ids).delete()

    if is_new_product and submitted_valid_variants:
        product.variants.exclude(id__in=seen_variant_ids).delete()

    gallery_images = request.FILES.getlist("gallery_images")
    current_count = product.extra_images.count()
    for offset, image in enumerate(gallery_images, start=1):
        ProductImage.objects.create(
            product=product,
            image=image,
            alt_text=product.inspired_by,
            sort_order=current_count + offset,
        )

    delete_image_ids = request.POST.getlist("delete_image")
    if delete_image_ids:
        product.extra_images.filter(id__in=delete_image_ids).delete()

    return product


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_product_add(request):
    if request.method == "POST":
        product = _save_product_from_admin_request(request)
        messages.success(request, "Product created.")
        return redirect("admin_product_edit", product_id=product.id)

    return render(request, "admin/product_form.html", {"product": None})


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_product_edit(request, product_id):
    product = get_object_or_404(
        Product.objects.prefetch_related("variants", "extra_images"),
        id=product_id,
    )
    if request.method == "POST":
        _save_product_from_admin_request(request, product)
        messages.success(request, "Product updated.")
        return redirect("admin_product_edit", product_id=product.id)

    return render(request, "admin/product_form.html", {"product": product})


@require_POST
@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted.")
    return redirect("admin_products")


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_hero(request):
    hero = HeroSection.objects.filter(is_active=True).first()

    if request.method == "POST":
        image = request.FILES.get("image")
        if image:
            HeroSection.objects.create(image=image, is_active=True)
            messages.success(request, "Hero image updated.")
            return redirect("admin_hero")
        messages.error(request, "Please choose an image to upload.")

    return render(request, "admin/hero.html", {"hero": hero})


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_bestsellers(request):
    search_query = request.GET.get("q", "").strip()
    products = Product.objects.order_by("inspired_by")
    if search_query:
        products = products.filter(
            Q(inspired_by__icontains=search_query)
            | Q(brand__icontains=search_query)
            | Q(category__icontains=search_query)
        )

    if request.method == "POST":
        selected_ids = request.POST.getlist("products")
        unique_ids = list(dict.fromkeys(selected_ids))
        if len(unique_ids) > 4:
            messages.error(request, "Please select no more than 4 bestseller products.")
        else:
            Product.objects.update(is_bestseller=False)
            Product.objects.filter(id__in=unique_ids).update(is_bestseller=True)
            messages.success(request, "Bestsellers updated.")
            return redirect("admin_bestsellers")

    product_ids = list(products.values_list("id", flat=True))
    hidden_selected_products = Product.objects.filter(is_bestseller=True).exclude(id__in=product_ids)
    selected_count = Product.objects.filter(is_bestseller=True).count()
    return render(
        request,
        "admin/bestsellers.html",
        {
            "products": products,
            "hidden_selected_products": hidden_selected_products,
            "search_query": search_query,
            "selected_count": selected_count,
        },
    )


@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_content(request):
    about_section, _ = AboutSection.objects.get_or_create(section_type=AboutSection.ABOUT)
    luxury_section, _ = AboutSection.objects.get_or_create(
        section_type=AboutSection.LUXURY,
        defaults={"title": "Luxury is not seen first. It is felt."},
    )

    if request.method == "POST":
        section_type = request.POST.get("section_type")
        section = {AboutSection.ABOUT: about_section, AboutSection.LUXURY: luxury_section}.get(section_type)

        if not section:
            messages.error(request, "Invalid content section.")
            return redirect("admin_content")

        section.title = request.POST.get("title", "").strip()
        image = request.FILES.get("image")
        if image:
            section.image = image
        section.save()
        messages.success(request, "Content section updated.")
        return redirect("admin_content")

    return render(
        request,
        "admin/content.html",
        {
            "about_section": about_section,
            "luxury_section": luxury_section,
        },
    )


@require_POST
@user_passes_test(_is_custom_admin, login_url="admin_login")
def admin_logout(request):
    logout(request)
    return redirect("admin_login")


def _place_orders_for_payload(user, payload, payment_meta=None):
    address_data = payload["address"]
    save_address = payload.get("save_address", False)
    shipping_method = payload["shipping_method"]
    shipping_fee = Decimal(payload["shipping_fee"])
    payment_method = payload["payment_method"]
    mode = payload["mode"]
    items = payload["items"]

    if save_address:
        address = SavedAddress(
            user=user,
            **address_data,
        )
        if not user.saved_addresses.exists():
            address.is_default = True
        address.save()

    created_orders = []
    per_order_shipping = shipping_fee / len(items) if mode == "cart" and items else shipping_fee

    for item in items:
        product = Product.objects.filter(id=item["product_id"]).first()
        variant = Variant.objects.filter(id=item["variant_id"]).first()
        quantity = int(item["quantity"])
        price = Decimal(item["price"])
        line_total = Decimal(item["total"])
        current_shipping = per_order_shipping if mode == "cart" else shipping_fee

        order = Order.objects.create(
            user=user,
            product=product,
            variant=variant,
            quantity=quantity,
            price=price,
            full_name=address_data["full_name"],
            email=address_data["email"],
            phone_number=address_data["phone_number"],
            address_line=address_data["address_line"],
            address_line_2=address_data["address_line_2"],
            city=address_data["city"],
            state=address_data["state"],
            country=address_data["country"],
            pincode=address_data["pincode"],
            landmark=address_data["landmark"],
            shipping_method=shipping_method,
            shipping_fee=current_shipping,
            total_amount=line_total + current_shipping,
            payment_method=payment_method,
            payment_status="Paid" if payment_meta else "Pending",
            is_paid=bool(payment_meta),
            razorpay_payment_id=payment_meta["razorpay_payment_id"] if payment_meta else "",
            razorpay_order_id=payment_meta["razorpay_order_id"] if payment_meta else "",
            razorpay_signature=payment_meta["razorpay_signature"] if payment_meta else "",
            status="Confirmed",
        )
        created_orders.append(order)

    return created_orders


def home(request):
    products = list(Product.objects.filter(is_bestseller=True).prefetch_related("variants")[:4])
    if len(products) < 4:
        selected_ids = [product.id for product in products]
        products.extend(
            Product.objects.exclude(id__in=selected_ids).prefetch_related("variants")[: 4 - len(products)]
        )

    return render(
        request,
        "store/home.html",
        {
            "products": products,
            "hero_section": HeroSection.objects.filter(is_active=True).first(),
            "about_section": AboutSection.objects.filter(section_type=AboutSection.ABOUT).first(),
            "luxury_section": AboutSection.objects.filter(section_type=AboutSection.LUXURY).first(),
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def about(request):
    return render(request, "store/about.html", {"wishlist_items": get_wishlist_ids(request)})


def policy_page(request, slug):
    page = POLICY_PAGES[slug]
    return render(
        request,
        "store/policy_page.html",
        {
            "page": page,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def contact_page(request):
    return render(
        request,
        "store/contact.html",
        {
            "page": CONTACT_PAGE,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def collection(request, category):
    products = Product.objects.all().prefetch_related("variants")

    if category != "all":
        products = products.filter(category=category)

    query = request.GET.get("q")
    if query:
        products = products.filter(
            Q(inspired_by__icontains=query)
            | Q(brand__icontains=query)
            | Q(top_note__icontains=query)
            | Q(middle_note__icontains=query)
            | Q(base_note__icontains=query)
            | Q(occasion__icontains=query)
        )

    brand = request.GET.get("brand")
    if brand:
        products = products.filter(brand__iexact=brand)

    occasion = request.GET.get("occasion")
    if occasion:
        products = products.filter(occasion__iexact=occasion)

    top_note = request.GET.get("top_note")
    if top_note:
        products = products.filter(top_note__icontains=top_note)

    middle_note = request.GET.get("middle_note")
    if middle_note:
        products = products.filter(middle_note__icontains=middle_note)

    base_note = request.GET.get("base_note")
    if base_note:
        products = products.filter(base_note__icontains=base_note)

    price = request.GET.get("price")
    if price:
        products = products.filter(variants__price__lte=price).distinct()

    sort = request.GET.get("sort")
    if sort == "az":
        products = products.order_by("inspired_by")
    elif sort == "za":
        products = products.order_by("-inspired_by")

    show = request.GET.get("show")

    filter_qs = Product.objects.all()
    if category != "all":
        filter_qs = filter_qs.filter(category=category)

    brands = (
        filter_qs.values_list("brand", flat=True)
        .exclude(brand__isnull=True)
        .exclude(brand="")
        .distinct()
        .order_by("brand")
    )

    occasions = (
        filter_qs.values_list("occasion", flat=True)
        .exclude(occasion__isnull=True)
        .exclude(occasion="")
        .distinct()
        .order_by("occasion")
    )

    def extract_notes(qs, field):
        notes = set()
        for value in qs.values_list(field, flat=True):
            if value:
                for item in value.split(","):
                    notes.add(item.strip())
        return sorted(notes)

    top_notes = extract_notes(filter_qs, "top_note")
    middle_notes = extract_notes(filter_qs, "middle_note")
    base_notes = extract_notes(filter_qs, "base_note")

    return render(
        request,
        "store/collection.html",
        {
            "products": products,
            "category": category,
            "brands": brands,
            "occasions": occasions,
            "top_notes": top_notes,
            "middle_notes": middle_notes,
            "base_notes": base_notes,
            "show": show,
            "query": query,
            "sort": sort,
            "selected_note": top_note or middle_note or base_note,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("account")

    form = SignupForm(request.POST or None)
    next_url = _get_safe_redirect(request)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Account created successfully.")
        return redirect(next_url)

    return render(
        request,
        "store/signup.html",
        {
            "form": form,
            "next": next_url,
            "google_login_url": _google_login_url(next_url),
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("account")

    form = LuxuryAuthenticationForm(request, data=request.POST or None)
    next_url = _get_safe_redirect(request)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)

        messages.success(request, "Welcome back.")
        return redirect(next_url)

    if request.method == "POST" and not form.is_valid():
        email = (request.POST.get("username") or "").strip().lower()
        if email and not User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email not found.")
        else:
            messages.error(request, "Incorrect credentials.")

    return render(
        request,
        "store/login.html",
        {
            "form": form,
            "next": next_url,
            "google_login_url": _google_login_url(next_url),
            "wishlist_items": get_wishlist_ids(request),
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")


@login_required(login_url="login")
def account_view(request):
    profile = request.user.profile
    profile_form = ProfileForm(
        request.POST if request.POST.get("form_name") == "profile" else None,
        instance=profile,
        user=request.user,
    )
    newsletter_form = NewsletterPreferencesForm(
        request.POST if request.POST.get("form_name") == "newsletter" else None,
        instance=profile,
    )

    if request.method == "POST" and request.POST.get("form_name") == "profile" and profile_form.is_valid():
        profile_form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("account")

    if request.method == "POST" and request.POST.get("form_name") == "newsletter" and newsletter_form.is_valid():
        newsletter_form.save()
        messages.success(request, "Your newsletter preferences have been updated.")
        return redirect("account")

    orders = request.user.orders.select_related("product", "variant")[:4]
    wishlist_products = Product.objects.filter(wishlisted_by__user=request.user).prefetch_related("variants")[:4]
    addresses = request.user.saved_addresses.all()[:3]

    return render(
        request,
        "store/account.html",
        {
            "profile_form": profile_form,
            "newsletter_form": newsletter_form,
            "orders": orders,
            "total_order_count": request.user.orders.count(),
            "wishlist_products": wishlist_products,
            "addresses": addresses,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


@login_required(login_url="login")
def my_orders(request):
    orders = request.user.orders.select_related("product", "variant").order_by("-created_at", "-id")
    paginator = Paginator(orders, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "store/my_orders.html",
        {
            "page_obj": page_obj,
            "orders": page_obj.object_list,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


@login_required(login_url="login")
def my_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("product", "variant"),
        id=order_id,
        user=request.user,
    )
    return render(
        request,
        "store/order_detail.html",
        {
            "order": order,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def cart_view(request):
    cart = request.session.get("cart", {})
    cart_items, subtotal = _build_cart_items(cart)
    shipping_fee = STANDARD_SHIPPING_FEE if cart_items else Decimal("0.00")
    total = subtotal + shipping_fee

    return render(
        request,
        "store/cart.html",
        {
            "cart_items": cart_items,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total": total,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


@require_POST
def update_cart_quantity(request, cart_key, action):
    cart = request.session.get("cart", {})

    if cart_key in cart:
        if action == "increase":
            cart[cart_key]["quantity"] += 1
        elif action == "decrease":
            cart[cart_key]["quantity"] -= 1

            if cart[cart_key]["quantity"] <= 0:
                del cart[cart_key]

        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")


@require_POST
def remove_from_cart(request, cart_key):
    cart = request.session.get("cart", {})

    if cart_key in cart:
        del cart[cart_key]
        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")


def product_detail(request, id):
    product = get_object_or_404(
        Product.objects.prefetch_related("variants", "extra_images"),
        id=id,
    )
    gallery_images = _gallery_images(product)
    return render(
        request,
        "store/product.html",
        {
            "product": product,
            "gallery_images": gallery_images,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


def add_to_cart(request, id):
    product = get_object_or_404(Product.objects.prefetch_related("extra_images"), id=id)
    cart = request.session.get("cart", {})
    quantity = _parse_quantity(request.GET.get("quantity", 1))

    variant_id = request.GET.get("variant")
    variant = product.variants.filter(id=variant_id).first() if variant_id else None

    if not variant:
        messages.error(request, "Please select a size before adding this fragrance to your bag.")
        return redirect("product_detail", id=product.id)

    cart_key = f"{id}_{variant.id}"
    if cart_key in cart:
        cart[cart_key]["quantity"] += quantity
    else:
        cart[cart_key] = {
            "name": product.inspired_by,
            "size": variant.size,
            "price": float(variant.price),
            "quantity": quantity,
            "image": _product_image_url(product),
        }

    request.session["cart"] = cart
    request.session.modified = True
    messages.success(request, "Fragrance added to bag.")
    return redirect("cart")


def search_products(request):
    query = request.GET.get("q")
    products = Product.objects.filter(
        Q(inspired_by__icontains=query)
        | Q(brand__icontains=query)
        | Q(top_note__icontains=query)
        | Q(middle_note__icontains=query)
        | Q(base_note__icontains=query)
        | Q(occasion__icontains=query)
    )

    return render(
        request,
        "store/search.html",
        {"products": products, "query": query, "wishlist_items": get_wishlist_ids(request)},
    )


def live_search(request):
    query = request.GET.get("q", "")
    products = Product.objects.filter(
        Q(inspired_by__icontains=query)
        | Q(brand__icontains=query)
        | Q(top_note__icontains=query)
        | Q(middle_note__icontains=query)
        | Q(base_note__icontains=query)
        | Q(occasion__icontains=query)
    )[:5]

    data = [{"name": p.inspired_by, "brand": p.brand, "url": f"/product/{p.id}/"} for p in products]
    return JsonResponse(data, safe=False)


def auth_required_modal(request):
    next_url = request.GET.get("next") or reverse("login")
    return JsonResponse(
        {
            "title": "Please sign in to save favourites.",
            "message": "Unlock your private fragrance shortlist and keep every signature scent within reach.",
            "login_url": f"{reverse('login')}?next={quote(next_url, safe='/?:=&')}",
            "signup_url": f"{reverse('signup')}?next={quote(next_url, safe='/?:=&')}",
        }
    )


def toggle_wishlist(request, id):
    product = get_object_or_404(Product, id=id)

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "requires_auth": True,
                "message": "Sign in to save favourites.",
                "modal_url": f"{reverse('auth_required_modal')}?next={reverse('product_detail', args=[id])}",
            },
            status=401,
        )

    wishlist_item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        wishlist_item.delete()
        in_wishlist = False
        message_text = "Removed from wishlist."
    else:
        in_wishlist = True
        message_text = "Added to wishlist."

    return JsonResponse(
        {
            "success": True,
            "in_wishlist": in_wishlist,
            "product_id": id,
            "count": WishlistItem.objects.filter(user=request.user).count(),
            "message": message_text,
        }
    )


@login_required(login_url="login")
def remove_from_wishlist(request, id):
    WishlistItem.objects.filter(user=request.user, product_id=id).delete()
    messages.success(request, "Favourite removed from your wishlist.")
    return redirect("wishlist")


def wishlist(request):
    if not request.user.is_authenticated:
        return _redirect_to_login(request, reverse("wishlist"), "Sign in to save favourites.")

    wishlist_products = (
        Product.objects.filter(wishlisted_by__user=request.user)
        .prefetch_related("variants")
        .distinct()
    )
    wishlist_ids = get_wishlist_ids(request)

    return render(
        request,
        "store/wishlist.html",
        {
            "wishlist_products": wishlist_products,
            "wishlist_items": wishlist_ids,
        },
    )


def buy_now_redirect(request, id):
    checkout_url = reverse("checkout", args=[id])
    query_parts = []
    if request.GET.get("variant"):
        query_parts.append(f"variant={request.GET.get('variant')}")
    if request.GET.get("quantity"):
        query_parts.append(f"quantity={request.GET.get('quantity')}")
    if query_parts:
        checkout_url = f"{checkout_url}?{'&'.join(query_parts)}"

    if not request.GET.get("variant"):
        messages.error(request, "Please select a size before continuing to checkout.")
        return redirect("product_detail", id=id)

    if not request.user.is_authenticated:
        return _redirect_to_login(request, checkout_url, "Please sign in to continue checkout.")
    return redirect(checkout_url)


@login_required(login_url="login")
def checkout(request, id):
    product = get_object_or_404(
        Product.objects.prefetch_related("variants", "extra_images"),
        id=id,
    )

    variant_id = request.GET.get("variant")
    variant = product.variants.filter(id=variant_id).first() if variant_id else None
    if not variant:
        messages.error(request, "Please select a size before continuing to checkout.")
        return redirect("product_detail", id=id)

    quantity = _parse_quantity(request.GET.get("quantity", 1))
    initial = _default_checkout_initial(request.user)
    form = CheckoutForm(request.POST or None, initial=initial)

    shipping_method = request.POST.get("shipping_method") or form.initial.get("shipping_method", "Standard")
    shipping_fee = _shipping_fee(shipping_method)
    checkout_items, subtotal = _single_checkout_item(product, variant, quantity)
    total_price = subtotal + shipping_fee

    if request.method == "POST" and form.is_valid():
        messages.info(request, "Use the Razorpay secure payment button to complete checkout.")

    return render(
        request,
        "store/checkout.html",
        _build_checkout_context(
            request,
            form=form,
            checkout_mode="single",
            checkout_items=checkout_items,
            subtotal=subtotal,
            shipping_method=shipping_method,
            shipping_fee=shipping_fee,
            total_price=total_price,
            product=product,
            variant=variant,
            quantity=quantity,
        ),
    )


@login_required(login_url="login")
def cart_checkout(request):
    cart = request.session.get("cart", {})
    cart_items, subtotal = _build_cart_items(cart)
    if not cart_items:
        messages.info(request, "Your bag is empty.")
        return redirect("cart")

    initial = _default_checkout_initial(request.user)
    form = CheckoutForm(request.POST or None, initial=initial)
    shipping_method = request.POST.get("shipping_method") or form.initial.get("shipping_method", "Standard")
    shipping_fee = _shipping_fee(shipping_method)
    total_price = subtotal + shipping_fee

    if request.method == "POST" and form.is_valid():
        messages.info(request, "Use the Razorpay secure payment button to complete checkout.")

    return render(
        request,
        "store/checkout.html",
        _build_checkout_context(
            request,
            form=form,
            checkout_mode="cart",
            checkout_items=cart_items,
            subtotal=subtotal,
            shipping_method=shipping_method,
            shipping_fee=shipping_fee,
            total_price=total_price,
        ),
    )


@require_POST
@login_required(login_url="login")
def create_razorpay_order(request):
    client = _get_razorpay_client()
    if not client:
        return JsonResponse(
            {"success": False, "message": "Razorpay keys are not configured yet."},
            status=503,
        )

    checkout_mode = request.POST.get("checkout_mode", "single")
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "success": False,
                "message": "Please review the highlighted checkout details.",
                "errors": form.errors,
            },
            status=400,
        )

    payment_method = form.cleaned_data["payment_method"]
    shipping_method = form.cleaned_data["shipping_method"]
    shipping_fee = _shipping_fee(shipping_method)

    if checkout_mode == "cart":
        cart_items, subtotal = _build_cart_items(request.session.get("cart", {}))
        if not cart_items:
            return JsonResponse({"success": False, "message": "Your bag is empty."}, status=400)
        items = cart_items
    else:
        product = get_object_or_404(Product.objects.prefetch_related("variants"), id=request.POST.get("product_id"))
        variant = get_object_or_404(Variant, id=request.POST.get("variant_id"), product=product)
        quantity = _parse_quantity(request.POST.get("quantity"))
        items, subtotal = _single_checkout_item(product, variant, quantity)

    total_price = subtotal + shipping_fee
    amount_paise = int(total_price * 100)
    receipt = f"jlt-{request.user.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    try:
        payment_order = client.order.create(
            {
                "amount": amount_paise,
                "currency": settings.RAZORPAY_CURRENCY,
                "receipt": receipt,
                "payment_capture": 1,
            }
        )
    except Exception:
        logger.exception("Failed to create Razorpay order")
        return JsonResponse(
            {"success": False, "message": "We could not initiate secure payment right now."},
            status=502,
        )

    payload = {
        "mode": checkout_mode,
        "items": [_serialize_pending_item(item) for item in items],
        "address": _serialize_address(form.cleaned_data),
        "save_address": form.cleaned_data.get("save_address", False),
        "shipping_method": shipping_method,
        "shipping_fee": _format_money(shipping_fee),
        "payment_method": payment_method,
        "razorpay_order_id": payment_order["id"],
        "amount": amount_paise,
    }
    request.session["pending_checkout"] = payload
    request.session.modified = True

    return JsonResponse(
        {
            "success": True,
            "key": settings.RAZORPAY_KEY_ID,
            "currency": settings.RAZORPAY_CURRENCY,
            "amount": amount_paise,
            "order_id": payment_order["id"],
            "name": "JLT Fragrances",
            "description": "Luxury Fragrance Order",
            "image": settings.BRAND_LOGO_URL,
            "prefill": {
                "name": form.cleaned_data["full_name"],
                "email": form.cleaned_data["email"],
                "contact": form.cleaned_data["phone_number"],
            },
            "notes": {
                "shipping_method": shipping_method,
                "payment_method": payment_method,
            },
            "verify_url": reverse("verify_razorpay_payment"),
        }
    )


@require_POST
@login_required(login_url="login")
def verify_razorpay_payment(request):
    pending_checkout = request.session.get("pending_checkout")
    if not pending_checkout:
        return JsonResponse(
            {"success": False, "message": "Your payment session has expired. Please try again."},
            status=400,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "message": "Invalid payment response."}, status=400)

    razorpay_payment_id = payload.get("razorpay_payment_id", "")
    razorpay_order_id = payload.get("razorpay_order_id", "")
    razorpay_signature = payload.get("razorpay_signature", "")

    if razorpay_order_id != pending_checkout.get("razorpay_order_id"):
        return JsonResponse({"success": False, "message": "Payment verification mismatch detected."}, status=400)

    client = _get_razorpay_client()
    if not client:
        return JsonResponse({"success": False, "message": "Razorpay keys are not configured yet."}, status=503)

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        payment_details = client.payment.fetch(razorpay_payment_id)
    except Exception:
        logger.exception("Razorpay signature verification failed")
        return JsonResponse(
            {"success": False, "message": "We could not verify this payment. Please try again."},
            status=400,
        )

    if payment_details.get("status") not in {"authorized", "captured"}:
        return JsonResponse(
            {"success": False, "message": "Payment was not completed successfully."},
            status=400,
        )

    orders = _place_orders_for_payload(
        request.user,
        pending_checkout,
        payment_meta={
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_signature": razorpay_signature,
        },
    )

    if pending_checkout["mode"] == "cart":
        request.session["cart"] = {}

    request.session["last_order_ids"] = [order.id for order in orders]
    request.session.pop("pending_checkout", None)
    request.session.modified = True
    _send_owner_notifications(orders)

    return JsonResponse(
        {
            "success": True,
            "redirect_url": reverse("checkout_success"),
        }
    )


@login_required(login_url="login")
def checkout_success(request):
    order_ids = request.session.get("last_order_ids", [])
    orders = request.user.orders.filter(id__in=order_ids).select_related("product", "variant")
    if not orders:
        return redirect("account")

    total_amount = sum(order.total_amount for order in orders)
    return render(
        request,
        "store/checkout_success.html",
        {
            "orders": orders,
            "total_amount": total_amount,
            "wishlist_items": get_wishlist_ids(request),
        },
    )


class LuxuryPasswordResetView(PasswordResetView):
    template_name = "store/password_reset.html"
    email_template_name = "store/emails/password_reset_email.txt"
    subject_template_name = "store/emails/password_reset_subject.txt"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        messages.success(
            self.request,
            "If an account exists for that email, a reset link has been sent.",
        )
        return super().form_valid(form)
