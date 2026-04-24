from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Order, Product
from .views import _send_owner_email_notification


User = get_user_model()


class OrderPagesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', email='owner@example.com', password='pass12345')
        self.other_user = User.objects.create_user(username='other', email='other@example.com', password='pass12345')
        self.product = Product.objects.create(inspired_by='Amber Reserve', category='like', brand='JLT')
        self.variant = self.product.variants.first()

        self.first_order = self._create_order(self.user, total_amount=Decimal('999.00'))
        self.second_order = self._create_order(self.user, total_amount=Decimal('1299.00'), payment_method='Razorpay')
        self.other_order = self._create_order(self.other_user, total_amount=Decimal('799.00'))

    def _create_order(self, user, *, total_amount, payment_method='Cash on Delivery'):
        return Order.objects.create(
            user=user,
            product=self.product,
            variant=self.variant,
            quantity=1,
            price=Decimal('999.00'),
            full_name='Client Name',
            email=user.email,
            phone_number='9999999999',
            address_line='123 Fragrance Street',
            city='Mumbai',
            state='Maharashtra',
            country='India',
            pincode='400001',
            shipping_method='Standard',
            shipping_fee=Decimal('0.00'),
            total_amount=total_amount,
            payment_method=payment_method,
            payment_status='Paid' if payment_method == 'Razorpay' else 'Pending',
            is_paid=payment_method == 'Razorpay',
            razorpay_payment_id='pay_12345' if payment_method == 'Razorpay' else '',
            status='Confirmed',
        )

    def test_my_orders_page_lists_only_logged_in_users_orders(self):
        self.client.login(username='owner', password='pass12345')
        response = self.client.get(reverse('my_orders'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'#{self.first_order.id}')
        self.assertContains(response, f'#{self.second_order.id}')
        self.assertNotContains(response, f'#{self.other_order.id}')
        self.assertEqual(list(response.context['page_obj'].object_list), [self.second_order, self.first_order])

    def test_my_order_detail_returns_404_for_other_users_order(self):
        self.client.login(username='owner', password='pass12345')
        response = self.client.get(reverse('my_order_detail', args=[self.other_order.id]))
        self.assertEqual(response.status_code, 404)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.gmail.com',
    EMAIL_HOST_USER='smtp-user@gmail.com',
    DEFAULT_FROM_EMAIL='JLT Fragrances <custom-sender@example.com>',
    OWNER_NOTIFICATION_EMAIL='orders@example.com',
)
class NotificationEmailTests(TestCase):
    def test_owner_email_falls_back_to_authenticated_gmail_sender(self):
        sent = _send_owner_email_notification('Subject', 'Body', [101])

        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['orders@example.com'])
        self.assertEqual(mail.outbox[0].from_email, 'JLT Fragrances <smtp-user@gmail.com>')

    def test_test_email_management_command_reports_success(self):
        stdout = StringIO()
        call_command('test_email', stdout=stdout)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Test email sent successfully', stdout.getvalue())
