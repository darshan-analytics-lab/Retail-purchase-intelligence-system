from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from account.models import Profile


class AccountAuthTests(TestCase):
    def test_signup_creates_user_with_full_name(self):
        response = self.client.post(reverse('signup'), {
            'full_name': 'Darshan Test',
            'username': 'darshan_test',
            'email': 'darshan@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
        })

        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(username='darshan_test')
        self.assertEqual(user.first_name, 'Darshan')
        self.assertEqual(user.last_name, 'Test')

    def test_signup_rejects_duplicate_email(self):
        User.objects.create_user(username='existing', email='same@example.com', password='StrongPass123!')

        response = self.client.post(reverse('signup'), {
            'full_name': 'New User',
            'username': 'newuser',
            'email': 'same@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_login_remember_me_sets_session_expiry(self):
        User.objects.create_user(username='member', password='StrongPass123!')

        response = self.client.post(reverse('login'), {
            'username': 'member',
            'password': 'StrongPass123!',
            'remember_me': '1',
        })

        self.assertRedirects(response, reverse('index'))
        self.assertGreater(self.client.session.get_expiry_age(), 60 * 60 * 24)

    def test_profile_page_displays_authenticated_user(self):
        user = User.objects.create_user(
            username='profileuser',
            password='StrongPass123!',
            first_name='Profile',
            last_name='User',
            email='profile@example.com',
        )
        Profile.objects.create(user=user, mobile='9999999999')
        self.client.login(username='profileuser', password='StrongPass123!')

        response = self.client.get(reverse('profile'))

        self.assertContains(response, 'Profile User')
        self.assertContains(response, '9999999999')
