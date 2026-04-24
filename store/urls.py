from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.policy_page, {"slug": "privacy"}, name='privacy_policy'),
    path('refund-policy/', views.policy_page, {"slug": "refund"}, name='refund_policy'),
    path('shipping-policy/', views.policy_page, {"slug": "shipping"}, name='shipping_policy'),
    path('contact-us/', views.contact_page, name='contact_us'),
    path('collection/<str:category>/', views.collection, name='collection'),

    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),
    path('forgot-password/', views.LuxuryPasswordResetView.as_view(), name='password_reset'),
    path('auth-modal/', views.auth_required_modal, name='auth_required_modal'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/checkout/', views.cart_checkout, name='cart_checkout'),
    path('cart/update/<str:cart_key>/<str:action>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<str:cart_key>/', views.remove_from_cart, name='remove_from_cart'),

    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:id>/', views.add_to_cart, name='add_to_cart'),

    path("live-search/", views.live_search, name="live_search"),
    path('wishlist/toggle/<int:id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/remove/<int:id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('buy-now/<int:id>/', views.buy_now_redirect, name='buy_now'),
    path('checkout/<int:id>/', views.checkout, name='checkout'),
    path('checkout/create-razorpay-order/', views.create_razorpay_order, name='create_razorpay_order'),
    path('checkout/verify-razorpay-payment/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
]
