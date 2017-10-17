import unittest
import logging
import json
from flask_api import status    # HTTP Status Codes
from server import Payment, PaymentStatus, PaymentMethodType, PaymentMethod, app, db

class TestServer(unittest.TestCase):

    def setUp(self):
        # Only log criticl errors
        app.debug = True
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.CRITICAL)
        # Set up the test database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
        db.drop_all()    # clean up the last tests
        db.create_all()  # make our sqlalchemy tables
        self.app = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_home(self):
    	"""GET the home page"""
    	resp = self.app.get('/')
    	self.assertTrue('Payments Home Page' in resp.data)

    def test_post_a_payment(self):
        """Create a payment using a POST"""
        js = {'user_id': 0, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        get_resp = self.app.get('/payments/1')
        p = Payment()
        p.deserialize(json.loads(get_resp.data))
        self.assertEqual(p.id, 1)

    def test_post_an_invalid_payment(self):
        """POST a payment with invalid information"""
        js = {'user_id': 0, 'order_id': 0, 'status': 'bad_data',
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue('body of request contained bad or no data' in resp.data)

    def test_post_a_payment_with_missing_information(self):
        """POST a payment with missing information"""
        js = {'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_a_payment(self):
        """Create a payment, then GET it"""
        js = {'user_id': 0, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp = self.app.get('/payments/1')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        p = Payment()
        p.deserialize(json.loads(resp.data))
        self.assertEqual(p.id, 1)
        self.assertEqual(p.user_id, js['user_id'])
        self.assertEqual(p.order_id, js['order_id'])
        self.assertEqual(p.status, PaymentStatus(js['status']))
        self.assertEqual(p.method_id, js['method_id'])

    def test_get_a_payment_404(self):
        """Try to GET a payment that doesn't exist"""
        resp = self.app.get('/payments/1')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_payments(self):
    	"""GET all payments in the database"""
        js = {'user_id': 0, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        js = {'user_id': 1, 'order_id': 1, 'status': PaymentStatus.PAID.value,
            'method_id': PaymentMethodType.DEBIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp = self.app.get('/payments')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), 2)

    def test_list_all_payment_methods(self):
        """Get all payment methods"""
        resp = self.app.get('/payments/methods')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(json.loads(resp.data)), len(PaymentMethodType))
        paymentMethodList = set(pm.name for pm in PaymentMethodType)
        responseList = set(json.loads(resp.data))
        self.assertTrue(paymentMethodList == responseList)

    def test_update_payment(self):
        """Update an existing Payment"""
        js = {'user_id': 0, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        js = {'user_id': 0, "order_id": 0, 'status': PaymentStatus.PAID.value, 
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.put('payments/1', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_json = json.loads(resp.data)
        self.assertEqual(new_json['status'], PaymentStatus.PAID.value)

    def test_update_payment_with_no_data(self):
        """ Update a Payment with no data passed """
        js = {'user_id': 0, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.app.put('/payments/1', data=None, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_payment_not_found(self):
        """Update a Payment that does not exist"""
        new_payment = {'user_id': 0, 'order_id': 0, 'status': 3, 'method_id': 1}
        data = json.dumps(new_payment)
        resp = self.app.put('/pets/4', data=data, content_type='application/json')
        self.assertEquals(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_payment_by_user(self):
        """ Query Payment by user ID """
        js = {'user_id': 1, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        js = {'user_id': 2, 'order_id': 0, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.app.get('/payments', query_string='user=2')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        query_item = data[0]
        self.assertEqual(query_item['user_id'], 2)

    def test_query_payment_by_order(self):
        """ Query Payment by order ID """
        js = {'user_id': 0, 'order_id': 1, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        js = {'user_id': 0, 'order_id': 2, 'status': PaymentStatus.UNPAID.value,
            'method_id': PaymentMethodType.CREDIT.value}
        resp = self.app.post('/payments', data=json.dumps(js), follow_redirects=True, content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.app.get('/payments', query_string='order=2')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 1)
        query_item = data[0]
        self.assertEqual(query_item['order_id'], 2)