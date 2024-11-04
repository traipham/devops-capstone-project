"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

######################################################################
#  T E S T   C A S E S
######################################################################


class TestAccountService(TestCase):
    
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        talisman.force_https = False
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_read_an_account(self):
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        resp_data = response.get_json()
        account_id = resp_data['id']

        get_response = self.client.get(BASE_URL+f'/{account_id}')
        get_resp_data = get_response.get_json()
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp_data['name'], account.name)
        # Negative scenario
        account_id = 101
        get_response = self.client.get(BASE_URL+f'/{account_id}')
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_accounts(self):
        # Empty list scenario
        get_response = self.client.get(BASE_URL)
        get_resp_data = get_response.get_json()
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, len(get_resp_data))
        accounts = self._create_accounts(5)
        # Positive scenario
        get_response = self.client.get(BASE_URL)
        get_resp_data = get_response.get_json()
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        for i in range(len(accounts)):
            self.assertEqual(accounts[i].email, get_resp_data[i]['email'])

    def test_update_account(self):
        mock_account = AccountFactory()
        mock_account_serial = mock_account.serialize()
        mock_account_serial.pop('id')
        account = self._create_accounts(1)[0]

        # Positive scenario
        post_resp = self.client.post(
            BASE_URL+f"/{account.id}",
            json=mock_account_serial,
            content_type="application/json"
        )
        get_resp_data = post_resp.get_json()
        self.assertEqual(post_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp_data['email'], mock_account_serial['email'])
        # Negative scenario: Bad account id
        post_resp = self.client.post(
            BASE_URL+"/101",
            json=mock_account_serial,
            content_type="application/json"
        )
        self.assertEqual(post_resp.status_code, status.HTTP_404_NOT_FOUND)
        # Negative scenario: Bad request body
        post_resp = self.client.post(
            BASE_URL+f"/{account.id}",
            json={"random": "value"},
            content_type="application/json"
        )
        self.assertEqual(post_resp.status_code, status.HTTP_409_CONFLICT)

    def test_delete_account(self):
        account = self._create_accounts(1)[0]
        # Positive scenario
        delete_resp = self.client.delete(BASE_URL+f"/{account.id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)
        # Negative scenario: bad account id
        delete_resp = self.client.delete(BASE_URL+"/101")
        self.assertEqual(delete_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_security_01(self):
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON
        )
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': 'default-src \'self\'; object-src \'none\'',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for k, v in headers.items():
            self.assertEqual(response.headers.get(k), v)

    def test_security_02(self):
        response = self.client.get(
            "/",
            environ_overrides=HTTPS_ENVIRON
        )
        self.assertIsNotNone(response.headers.get("Access-Control-Allow-Origin"))
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
