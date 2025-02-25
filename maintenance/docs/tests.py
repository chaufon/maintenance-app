from django.conf import settings
from django.test import TestCase

from apps.users.models import Rol, User


class LoginTestCase(TestCase):
    fixtures = ["test_roles.json", "test_users.json"]

    @classmethod
    def setUpTestData(cls):
        cls.rol_asesor = Rol.objects.get(pk=3)
        cls.rol_supervisor = Rol.objects.get(pk=2)
        cls.rol_coordinador = Rol.objects.get(pk=1)
        cls.coordinador = User.objects.filter(rol=cls.rol_coordinador).first()

    def setUp(self):
        self.data_test_user = {
            "username": "90000000",
            "email": "a@b.com",
            "password": "test_password",
            "first_name": "test_nombre",
            "last_name": "test_apellido",
            "document_type": 1,  # DNI
            "document_number": "99999999",
            "external_user": "99999999",
            "rol": self.rol_supervisor,
            "manager": self.coordinador,
        }
        self.supervisor = User.objects.create_user(**self.data_test_user)

    def test_get_login_page(self):
        response = self.client.get(settings.LOGIN_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "maintenance/login.html")

    def test_succesful_login(self):
        response = self.client.post(
            settings.LOGIN_URL, {"username": "90000000", "password": "test_password"}
        )
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_failed_login(self):
        response = self.client.post(
            settings.LOGIN_URL, {"username": "90000000", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "maintenance/login.html")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_failed_login_disabled_user(self):
        self.supervisor.is_active = False
        self.supervisor.save()
        response = self.client.post(
            settings.LOGIN_URL, {"username": "90000000", "password": "test_password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "maintenance/login.html")
        self.assertFalse(response.wsgi_request.user.is_authenticated)
