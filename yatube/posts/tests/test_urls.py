from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.list_urls_all_client = [
            'posts/index.html',
            'posts/group_list.html',
            'posts/profile.html'
        ]
        cls.list_urls_authorized_client = [
            'posts/post_detail.html',
            'posts/create_post.html',
            'posts/follow.html',
        ]
        cls.url_names = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.post.author}/': 'posts/profile.html',
            f'/posts/{cls.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        cls.url_names_social = [
            reverse(
                'posts:add_comment', kwargs={'post_id': cls.post.pk}
            ),
            reverse(
                'posts:profile_follow', kwargs={'username': cls.post.author}
            ),
            reverse(
                'posts:profile_unfollow', kwargs={'username': cls.post.author}
            ),
        ]

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author = User.objects.create_user(username='author')
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_pages_url_exists_at_desired_location_not_auth(self):
        """Страницы /posts/ доступные любому пользователю."""
        for address, template in StaticURLTests.url_names.items():
            if template in self.list_urls_all_client:
                with self.subTest(address=address,
                                  template=template):
                    response = self.guest_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_url_exists_at_desired_location_auth(self):
        """Страницы /posts/ доступные авторизированному пользователю."""
        for address, template in StaticURLTests.url_names.items():
            if template in self.list_urls_authorized_client:
                with self.subTest(address=address, template=template):
                    response = self.authorized_client.get(address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_detail_url_exists_at_desired_location_authorized(self):
        """Страница /post_edit/ доступна автору поста."""
        if self.authorized_author == self.user:
            response = self.author.get(f'/posts/{self.post.id}/edit/')
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_edit_list_url_redirect_anonymous(self):
        """Страница /post_edit/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get(
            '/posts/cls.post.id/edit/', follow=True
        )
        self.assertRedirects(
            response, '/auth/login/?next=/posts/cls.post.id/edit/'
        )

    def test_create_url_redirect_anonymous(self):
        """Страница /create/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_urls_uses_correct_template_auth(self):
        """URL-адрес использует соответствующий шаблон/авторизованный."""
        for address, template in StaticURLTests.url_names.items():
            if template in self.list_urls_authorized_client:
                with self.subTest(address=address):
                    response = self.authorized_author.get(address)
                    self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_template_not_auth(self):
        """URL-адрес использует соответствующий шаблон/неавторизованный."""
        for address, template in StaticURLTests.url_names.items():
            if template in self.list_urls_all_client:
                with self.subTest(address=address):
                    response = self.guest_client.get(address)
                    self.assertTemplateUsed(response, template)

    def test_unexisting_page_added_url_exists_at_desired_location(self):
        """Страница /unexisting_page/ доступна любому пользователю."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_url_404_error_uses_correct_template(self):
        """ Тест на кастомный шаблон при ошибке 404 """
        response = self.guest_client.get('/smtn')
        self.assertTemplateUsed(response, 'core/404.html')

    def test_redirects_for_comment_and_follow(self):
        """Проверка редиректа при комментировании и подписке/отписке"""
        for address in self.url_names_social:
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, f'/auth/login/?next={address}')
