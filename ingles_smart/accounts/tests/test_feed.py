from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils.datastructures import MultiValueDict

from accounts.models import Perfil
from feed.models import Post
from accounts.views import (
    _feed_has_attachments,
    _feed_html_is_empty,
    _feed_upload_is_valid,
)


@override_settings(ALLOWED_HOSTS=["testserver"])
class FeedPublishTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username="prof_feed",
            password="test-pass-123",
            first_name="Prof",
            last_name="Feed",
        )
        profs, _ = Group.objects.get_or_create(name="Professores")
        self.user.groups.add(profs)
        perfil = self.user.perfil
        perfil.deve_trocar_senha = False
        perfil.save(update_fields=["deve_trocar_senha"])
        self.client.force_login(self.user)

    def test_empty_html_detection(self):
        self.assertTrue(_feed_html_is_empty(""))
        self.assertTrue(_feed_html_is_empty("<p><br></p>"))
        self.assertFalse(_feed_html_is_empty("<p>Hello</p>"))

    def test_upload_is_valid_rejects_empty(self):
        empty = SimpleUploadedFile("empty.bin", b"", content_type="image/png")
        self.assertFalse(_feed_upload_is_valid(empty))
        real = SimpleUploadedFile("photo.png", b"x", content_type="image/png")
        self.assertTrue(_feed_upload_is_valid(real))

    def test_has_attachments_ignores_empty_files(self):
        files = MultiValueDict()
        files.setlist(
            "imagens",
            [SimpleUploadedFile("empty.bin", b"", content_type="image/png")],
        )
        self.assertFalse(_feed_has_attachments(files))

    def test_publish_text_only(self):
        response = self.client.post(
            "/feed/",
            {"conteudo": "<p>Hello from test</p>"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Post.objects.filter(conteudo__icontains="Hello from test").exists())

    def test_publish_text_with_empty_file_parts(self):
        empty = SimpleUploadedFile("empty.bin", b"", content_type="application/octet-stream")
        response = self.client.post(
            "/feed/",
            {
                "conteudo": "<p>Text with empty file parts</p>",
                "imagens": empty,
                "arquivos": empty,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        post = Post.objects.get(conteudo__icontains="Text with empty file parts")
        self.assertEqual(post.imagens.count(), 0)
        self.assertEqual(post.arquivos.count(), 0)
