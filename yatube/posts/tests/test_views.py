import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, override_settings, TestCase
from django.urls import reverse
from posts.models import Follow, Group, Post
from posts.forms import PostForm
from posts.settings import POSTS_PER_PAGE
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_empty = Group.objects.create(
            title='Пустая группа',
            slug='test_slug_empty_group'
        )
        cls.post = Post.objects.create(
            author=PostViewTests.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded,
        )
        # cls.comment = Comment.objects.create(
        #     text='Тестовый текст комментария',
        # )
        cls.posts_pages_reverse = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={
                    'username': cls.user.username}),
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        test_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост авторизованного юзера'
        )
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={
                'slug': PostViewTests.group.slug
            }):
            'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={
                    'username': PostViewTests.user.username
                }
            ):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': test_post.pk}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': test_post.pk}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_post_show_in_correct_pages(self):
        """ Пост отображается на главной странице и на странице группы,
        указанной при создании, не отображатеся в другой группе."""
        for reverse_name in self.posts_pages_reverse:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                post = response.context['page_obj'][0]
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(
                    post.author.username, PostViewTests.user.username
                )
                self.assertEqual(post.group.title, self.post.group.title)
                self.assertEqual(post.image,
                                 self.post.image)
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={
                'slug': 'test_slug_empty_group'
            })
        )
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': PostViewTests.post.pk})
        )
        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)

    def test_cache(self):
        """ Тестирование работы кэша"""
        response_no_post = self.authorized_client.get(reverse('posts:index'))
        post = Post.objects.create(text='test', author=self.user)
        response_exist_post = self.authorized_client.get(
            reverse('posts:index'))
        Post.objects.filter(id=post.id).delete()
        response_post_delete = self.authorized_client.get(
            reverse('posts:index'))
        self.assertEqual(
            response_exist_post.content,
            response_post_delete.content
        )
        cache.clear()
        response_after_delete = self.authorized_client.get(
            reverse('posts:index'))
        self.assertTrue(
            response_after_delete.context['page_obj'].count,
            response_no_post.context['page_obj'].count)

    def test_authorized_user_follow(self):
        """ Подписка авторизованным пользователем """
        new_user = User.objects.create(username='Cat')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        new_authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user.username}
        ))
        self.assertTrue(Follow.objects.filter(
            user=new_user, author=self.user
        ).exists())

    def test_authorized_user_unfollow(self):
        """Отписка авторизованным пользователем """
        new_user = User.objects.create(username='Cat')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        new_authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user.username}
        ))
        new_authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user.username}
        ))
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_post_authorized_user(self):
        """Новый пост есть у подписчиков/нет у других"""
        Post.objects.create(
            author=self.user,
            text=self.post.text)
        Follow.objects.create(user=PostViewTests.user, author=self.user)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, self.post.text)
        client = User.objects.create(username='Cat')
        self.client = Client()
        self.client.force_login(client)
        response = self.client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_add_comment(self):
        """Авторизированный пользователь создает комментарий"""
        post = Post.objects.last()
        form_data = {
            'text': 'Тестовый текст комментария',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        response1 = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}
            )
        )
        self.assertEqual(len(response1.context['comments']), 1)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth1')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test_slug2',
            description='Описание')
        cls.posts = []
        for i in range(POSTS_PER_PAGE + 3):
            Post.objects.create(
                text=f'Test-{i}',
                author=cls.author,
                group=cls.group,
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='noname')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_contains_ten_records(self):
        """Проверка: количество постов на первой странице равно 10."""
        test_cases = [
            reverse(
                'posts:profile',
                kwargs={'username': PaginatorViewsTest.author.username}
            ),
            reverse(
                'posts:group_list',
                kwargs={'slug': PaginatorViewsTest.group.slug}
            ),
            reverse('posts:index'),
        ]
        for expected in test_cases:
            with self.subTest(expected=expected):
                response = self.client.get(expected)
                self.assertEqual(len(
                    response.context['page_obj']
                ), POSTS_PER_PAGE)

    def test_pages_contains_three_records(self):
        """Проверка: на второй странице должно быть три поста."""
        test_cases = [
            reverse(
                'posts:profile',
                kwargs={'username': PaginatorViewsTest.author.username}
            ) + '?page=2',
            reverse(
                'posts:group_list',
                kwargs={'slug': PaginatorViewsTest.group.slug}
            ) + '?page=2',
            reverse('posts:index') + '?page=2',
        ]
        for expected in test_cases:
            with self.subTest(expected=expected):
                response = self.client.get(expected)
                self.assertEqual(len(response.context['page_obj']), 3)
