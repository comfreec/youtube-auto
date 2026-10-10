import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import app.services.license as client_license
import seller_license_server as server


class LicenseSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private_path = self.root / "private.pem"
        self.public_path = self.root / "public.pem"
        self.database_path = self.root / "database.json"
        private_key = Ed25519PrivateKey.generate()
        self.private_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        self.public_path.write_bytes(
            private_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_server_certificate_is_machine_bound_and_signed(self):
        record = {
            "id": "license-id",
            "expires_at": "2099-12-31T23:59:59+00:00",
        }
        with patch.object(server, "PRIVATE_KEY_FILE", self.private_path), patch.object(
            client_license, "PUBLIC_KEY_FILE", self.public_path
        ):
            certificate = server.issue_certificate(record, "hardware-a")
            manager = client_license.LicenseManager()
            payload = manager._verify_certificate(certificate, "hardware-a")
            self.assertEqual(payload["license_id"], "license-id")
            with self.assertRaises(RuntimeError):
                manager._verify_certificate(certificate, "hardware-b")

    def test_private_key_is_not_the_public_key(self):
        self.assertNotEqual(self.private_path.read_bytes(), self.public_path.read_bytes())

    def test_admin_requires_strong_environment_password(self):
        with patch.dict(os.environ, {"LICENSE_ADMIN_PASSWORD": "short"}, clear=False):
            with self.assertRaises(RuntimeError):
                server.admin_password()

    def test_public_api_has_no_admin_routes(self):
        public_paths = {route.path for route in server.public_app.routes}
        admin_paths = {route.path for route in server.admin_app.routes}
        self.assertNotIn("/admin", public_paths)
        self.assertNotIn("/admin/api/licenses", public_paths)
        self.assertIn("/admin", admin_paths)


if __name__ == "__main__":
    unittest.main()
