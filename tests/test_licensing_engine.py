import base64
import hashlib
import json
import copy
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import date

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from database.licensing_engine import (
    cihaz_parmak_izi_olustur,
    firma_parmak_izi_olustur,
    lisans_anahtari_sha256,
    aktif_lisans_durumunu_getir,
    lisans_acik_anahtarlarini_yukle,
    lisans_erisim_karari,
    lisans_talep_bilgilerini_getir,
    lisans_anahtarini_dogrula,
    lisansi_aktive_et,
)
from database.migrations import run_migrations


def b64url(value):
    return base64.urlsafe_b64encode(
        value
    ).decode("ascii").rstrip("=")


class LicensingEngineTest(unittest.TestCase):

    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_raw = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_keys = {
            "REDBOX-TEST-1": base64.b64encode(
                public_raw
            ).decode("ascii")
        }
        self.company_hash = firma_parmak_izi_olustur(
            "Test Gıda A.Ş.",
            "Test Gıda",
            "1234567890",
        )
        self.device_hash = cihaz_parmak_izi_olustur(
            "TEST-DEVICE-001",
            "TEST",
        )["cihaz_parmak_izi_sha256"]

    def token(self, **changes):
        payload = {
            "sozlesme_surumu": 1,
            "lisans_uuid": "LIC-TEST-001",
            "urun_kodu": "REDBOX_OS",
            "acik_anahtar_kimligi": "REDBOX-TEST-1",
            "firma_parmak_izi_sha256": self.company_hash,
            "cihaz_parmak_izi_sha256": self.device_hash,
            "lisans_turu": "SURELI",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": "2026-12-31",
            "grace_period_gun": 7,
            "duzenlenme_zamani": "2026-01-01T09:00:00+03:00",
        }
        payload.update(changes)
        payload_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        signature = self.private_key.sign(payload_bytes)
        return (
            "RBX1."
            + b64url(payload_bytes)
            + "."
            + b64url(signature)
        )

    def verify(self, token, today):
        return lisans_anahtarini_dogrula(
            token,
            self.public_keys,
            self.company_hash,
            self.device_hash,
            simdi=today,
        )

    def test_valid_timed_license(self):
        result = self.verify(
            self.token(),
            date(2026, 7, 21),
        )
        self.assertTrue(result["gecerli"])
        self.assertEqual(result["durum"], "AKTIF")
        self.assertEqual(
            result["neden_kodu"],
            "LISANS_GECERLI",
        )

    def test_perpetual_license(self):
        result = self.verify(
            self.token(
                lisans_turu="SURESIZ",
                bitis_tarihi=None,
            ),
            date(2036, 7, 21),
        )
        self.assertTrue(result["gecerli"])
        self.assertEqual(result["durum"], "AKTIF")

    def test_grace_period_and_expiry(self):
        grace = self.verify(
            self.token(),
            date(2027, 1, 5),
        )
        expired = self.verify(
            self.token(),
            date(2027, 1, 8),
        )
        self.assertTrue(grace["gecerli"])
        self.assertEqual(grace["durum"], "GRACE")
        self.assertEqual(grace["kalan_grace_gun"], 2)
        self.assertFalse(expired["gecerli"])
        self.assertEqual(
            expired["durum"],
            "SURESI_DOLDU",
        )

    def test_tampered_token_is_rejected(self):
        token = self.token()
        prefix, payload, signature = token.split(".")
        raw = bytearray(
            base64.urlsafe_b64decode(
                payload + "=" * (-len(payload) % 4)
            )
        )
        raw[-2] ^= 1
        tampered = (
            prefix
            + "."
            + b64url(bytes(raw))
            + "."
            + signature
        )
        result = self.verify(
            tampered,
            date(2026, 7, 21),
        )
        self.assertFalse(result["gecerli"])
        self.assertIn(
            result["neden_kodu"],
            {
                "ANAHTAR_COZULEMEDI",
                "IMZA_GECERSIZ",
                "PAYLOAD_KANONIK_DEGIL",
            },
        )

    def test_wrong_company_and_device_are_rejected(self):
        wrong_company = lisans_anahtarini_dogrula(
            self.token(),
            self.public_keys,
            hashlib.sha256(b"wrong-company").hexdigest(),
            self.device_hash,
            simdi=date(2026, 7, 21),
        )
        wrong_device = lisans_anahtarini_dogrula(
            self.token(),
            self.public_keys,
            self.company_hash,
            hashlib.sha256(b"wrong-device").hexdigest(),
            simdi=date(2026, 7, 21),
        )
        self.assertEqual(
            wrong_company["neden_kodu"],
            "FIRMA_UYUSMUYOR",
        )
        self.assertEqual(
            wrong_device["neden_kodu"],
            "CIHAZ_UYUSMUYOR",
        )

    def test_device_raw_identifier_is_not_exposed(self):
        result = cihaz_parmak_izi_olustur(
            "PRIVATE-RAW-DEVICE-ID",
            "TEST",
        )
        self.assertEqual(
            len(result["cihaz_parmak_izi_sha256"]),
            64,
        )
        self.assertNotIn(
            "PRIVATE-RAW-DEVICE-ID",
            str(result),
        )

    def test_license_key_hash_is_stable(self):
        token = self.token()
        self.assertEqual(
            lisans_anahtari_sha256(token),
            hashlib.sha256(
                token.encode("utf-8")
            ).hexdigest(),
        )




class LicensingActivationTest(LicensingEngineTest):

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = (
            Path(self.temp_dir.name)
            / "licensing_activation.db"
        )
        project_root = Path(__file__).resolve().parents[1]
        shutil.copy2(
            project_root / "database" / "redbox_os.db",
            self.db_path,
        )
        run_migrations(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            """
            INSERT INTO firma_profili (
                id,
                ticari_unvan,
                kisa_ad,
                vergi_no,
                kayit_zamani
            )
            VALUES (
                1,
                'Test Gıda A.Ş.',
                'Test Gıda',
                '1234567890',
                '2026-07-21T01:00:00+03:00'
            )
            """
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def activate(self, token=None):
        return lisansi_aktive_et(
            self.conn,
            token or self.token(),
            self.public_keys,
            1,
            self.device_hash,
            kullanici={
                "hesap_id": 1,
                "kullanici_adi": "test-admin",
                "ad_soyad": "Test Admin",
            },
            oturum_id="com2-activation-test",
            simdi="2026-07-21T01:05:00+03:00",
        )

    def test_atomic_activation_creates_full_contract(self):
        token = self.token()
        result = self.activate(token)

        license_row = self.conn.execute(
            """
            SELECT
                lisans_uuid,
                lisans_anahtari_sha256,
                durum,
                lisans_turu
            FROM lisans_kayitlari
            """
        ).fetchone()
        validation = self.conn.execute(
            """
            SELECT
                sonuc,
                kaynak,
                neden_kodu
            FROM lisans_dogrulama_kayitlari
            """
        ).fetchone()
        audit = self.conn.execute(
            """
            SELECT
                modul,
                islem,
                kayit_turu,
                oturum_id
            FROM denetim_kayitlari
            WHERE modul = 'LISANS'
            """
        ).fetchone()

        self.assertEqual(result["durum"], "AKTIF")
        self.assertEqual(
            license_row,
            (
                "LIC-TEST-001",
                hashlib.sha256(
                    token.encode("utf-8")
                ).hexdigest(),
                "AKTIF",
                "SURELI",
            ),
        )
        self.assertEqual(
            validation,
            (
                "BASARILI",
                "AKTIVASYON",
                "LISANS_GECERLI",
            ),
        )
        self.assertEqual(
            audit,
            (
                "LISANS",
                "OLUSTURMA",
                "lisans_aktivasyonu",
                "com2-activation-test",
            ),
        )

        stored_values = " ".join(
            str(value)
            for value in self.conn.execute(
                """
                SELECT
                    imzali_payload_json,
                    imza_base64,
                    lisans_anahtari_sha256
                FROM lisans_kayitlari
                """
            ).fetchone()
        )
        self.assertNotIn(token, stored_values)

    def test_second_active_license_is_rejected(self):
        self.activate()

        with self.assertRaises(RuntimeError):
            self.activate(
                self.token(
                    lisans_uuid="LIC-TEST-002",
                )
            )

        count = self.conn.execute(
            "SELECT COUNT(*) FROM lisans_kayitlari"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_invalid_license_writes_nothing(self):
        with self.assertRaises(ValueError):
            self.activate(self.token() + "tamper")

        counts = (
            self.conn.execute(
                "SELECT COUNT(*) FROM lisans_kayitlari"
            ).fetchone()[0],
            self.conn.execute(
                """
                SELECT COUNT(*)
                FROM lisans_dogrulama_kayitlari
                """
            ).fetchone()[0],
            self.conn.execute(
                """
                SELECT COUNT(*)
                FROM denetim_kayitlari
                WHERE modul = 'LISANS'
                """
            ).fetchone()[0],
        )
        self.assertEqual(counts, (0, 0, 0))



    def test_active_license_status_is_revalidated(self):
        self.activate()

        result = aktif_lisans_durumunu_getir(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertTrue(result["gecerli"])
        self.assertEqual(result["durum"], "AKTIF")
        self.assertEqual(
            result["neden_kodu"],
            "LISANS_GECERLI",
        )

    def test_expired_license_is_detected_read_only(self):
        self.activate()

        before_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM lisans_dogrulama_kayitlari
            """
        ).fetchone()[0]

        result = aktif_lisans_durumunu_getir(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2027-01-08T02:00:00+03:00",
        )

        after_count = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM lisans_dogrulama_kayitlari
            """
        ).fetchone()[0]

        self.assertFalse(result["gecerli"])
        self.assertEqual(
            result["durum"],
            "SURESI_DOLDU",
        )
        self.assertEqual(before_count, after_count)

    def test_clock_rollback_is_rejected(self):
        self.activate()

        result = aktif_lisans_durumunu_getir(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-20T23:00:00+03:00",
        )

        self.assertFalse(result["gecerli"])
        self.assertEqual(
            result["neden_kodu"],
            "SISTEM_SAATI_GERI_ALINDI",
        )

    def test_modified_stored_signature_is_rejected(self):
        self.activate()

        self.conn.execute(
            """
            UPDATE lisans_kayitlari
            SET imza_base64 = imza_base64 || 'x'
            """
        )
        self.conn.commit()

        result = aktif_lisans_durumunu_getir(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertFalse(result["gecerli"])
        self.assertIn(
            result["neden_kodu"],
            {
                "LISANS_KAYDI_DEGISTIRILMIS",
                "IMZA_GECERSIZ",
            },
        )



    def test_legacy_transition_allows_normal_login(self):
        result = lisans_erisim_karari(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertTrue(result["erisim_izni"])
        self.assertEqual(
            result["durum"],
            "GECIS_SURESI",
        )
        self.assertEqual(
            result["akis"],
            "NORMAL_GIRIS",
        )

    def test_expired_transition_requires_activation(self):
        self.conn.execute(
            """
            UPDATE lisans_gecis_durumu
            SET bitis_zamani = '2026-07-20T00:00:00+03:00'
            WHERE id = 1
            """
        )
        self.conn.commit()

        result = lisans_erisim_karari(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertFalse(result["erisim_izni"])
        self.assertEqual(
            result["durum"],
            "GECIS_SURESI_DOLDU",
        )
        self.assertEqual(
            result["akis"],
            "LISANS_AKTIVASYONU",
        )

    def test_initial_setup_is_allowed_without_license(self):
        self.conn.execute(
            "DELETE FROM lisans_gecis_durumu"
        )
        self.conn.execute(
            "DELETE FROM kullanici_hesaplari"
        )
        self.conn.execute(
            "DELETE FROM personel_yetkileri"
        )
        self.conn.execute(
            "DELETE FROM personeller"
        )
        self.conn.commit()

        result = lisans_erisim_karari(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertTrue(result["erisim_izni"])
        self.assertEqual(
            result["durum"],
            "ILK_KURULUM",
        )
        self.assertEqual(
            result["akis"],
            "ILK_KURULUM",
        )

    def test_invalid_stored_license_cannot_use_transition(self):
        self.activate()
        self.conn.execute(
            """
            UPDATE lisans_kayitlari
            SET imza_base64 = imza_base64 || 'x'
            """
        )
        self.conn.commit()

        result = lisans_erisim_karari(
            self.conn,
            self.public_keys,
            self.device_hash,
            simdi="2026-07-21T02:00:00+03:00",
        )

        self.assertFalse(result["erisim_izni"])
        self.assertEqual(result["akis"], "LISANS")



    def test_license_request_contains_hashed_identity(self):
        request = lisans_talep_bilgilerini_getir(
            self.conn,
            cihaz_bilgisi={
                "cihaz_parmak_izi_sha256": self.device_hash,
                "kaynak": "TEST",
            },
            simdi="2026-07-21T01:30:00+03:00",
        )

        self.assertTrue(request["hazir"])
        self.assertEqual(
            request["firma_parmak_izi_sha256"],
            self.company_hash,
        )
        self.assertEqual(
            request["cihaz_parmak_izi_sha256"],
            self.device_hash,
        )
        self.assertNotIn(
            "TEST-DEVICE-001",
            str(request),
        )

    def test_activation_completes_transition(self):
        self.activate()

        transition = self.conn.execute(
            """
            SELECT
                durum,
                tamamlanma_zamani
            FROM lisans_gecis_durumu
            WHERE id = 1
            """
        ).fetchone()

        self.assertEqual(
            transition[0],
            "TAMAMLANDI",
        )
        self.assertIsNotNone(transition[1])

    def test_audit_failure_rolls_back_activation(self):
        self.conn.execute(
            """
            CREATE TRIGGER com2_block_license_audit
            BEFORE INSERT ON denetim_kayitlari
            WHEN NEW.modul = 'LISANS'
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'forced license audit failure'
                );
            END
            """
        )
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.activate()

        counts = (
            self.conn.execute(
                "SELECT COUNT(*) FROM lisans_kayitlari"
            ).fetchone()[0],
            self.conn.execute(
                """
                SELECT COUNT(*)
                FROM lisans_dogrulama_kayitlari
                """
            ).fetchone()[0],
        )
        self.assertEqual(counts, (0, 0))




class PublicKeyRegistryTest(unittest.TestCase):

    def setUp(self):
        self.project_root = Path(
            __file__
        ).resolve().parents[1]
        self.registry_path = (
            self.project_root
            / "licensing"
            / "public_keys.json"
        )
        self.registry = json.loads(
            self.registry_path.read_text(
                encoding="utf-8"
            )
        )
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_registry(self, value):
        path = (
            Path(self.temp_dir.name)
            / "public_keys.json"
        )
        path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_production_public_registry_loads(self):
        keys = lisans_acik_anahtarlarini_yukle(
            self.registry_path
        )

        self.assertEqual(len(keys), 1)
        self.assertIn(
            "REDBOX-PROD-2813E117AB41",
            keys,
        )

    def test_wrong_product_registry_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["product_code"] = "WRONG_PRODUCT"

        with self.assertRaises(ValueError):
            lisans_acik_anahtarlarini_yukle(
                self.write_registry(registry)
            )

    def test_modified_public_key_hash_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["keys"][0][
            "public_key_sha256"
        ] = "0" * 64

        with self.assertRaises(ValueError):
            lisans_acik_anahtarlarini_yukle(
                self.write_registry(registry)
            )

    def test_non_ed25519_algorithm_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["keys"][0][
            "algorithm"
        ] = "HMAC-SHA256"

        with self.assertRaises(ValueError):
            lisans_acik_anahtarlarini_yukle(
                self.write_registry(registry)
            )

    def test_no_active_key_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        registry["keys"][0]["active"] = False

        with self.assertRaises(ValueError):
            lisans_acik_anahtarlarini_yukle(
                self.write_registry(registry)
            )


if __name__ == "__main__":
    unittest.main()
