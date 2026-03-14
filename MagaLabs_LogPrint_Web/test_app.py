import unittest
from app import app, db, Ticket

class MagaLabsTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_solicitar_ticket(self):
        response = self.app.post('/solicitar', data=dict(
            zendesk_id='#12345',
            solicitor_name='Test User',
            solicitor_login='test.user',
            solicitor_id='9999',
            solicitor_sector='IT',
            solicitor_cd='CD01',
            asset_type='Printer',
            asset_identifier='HP M404',
            problem_description='Toner Low'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with app.app_context():
            ticket = Ticket.query.first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.zendesk_id, '#12345')
            self.assertEqual(ticket.status, 'Open')

    def test_resolve_ticket(self):
        # Create ticket first
        with app.app_context():
            ticket = Ticket(
                zendesk_id='#54321',
                solicitor_name='User 2',
                solicitor_login='user.2',
                solicitor_id='8888',
                solicitor_sector='HR',
                solicitor_cd='CD02',
                asset_type='Computer',
                asset_identifier='PC-HR-01',
                problem_description='Slow PC'
            )
            db.session.add(ticket)
            db.session.commit()
            ticket_id = ticket.id

        # Resolve it
        response = self.app.post(f'/resolver/{ticket_id}', data=dict(
            resolver_name='Tech Guy',
            resolver_login='tech.guy',
            resolver_id='7777',
            toner_model='',
            counter_number='',
            resolution_note='Fixed it'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        with app.app_context():
            ticket = Ticket.query.get(ticket_id)
            self.assertEqual(ticket.status, 'Closed')
            self.assertEqual(ticket.resolver_name, 'Tech Guy')

if __name__ == '__main__':
    unittest.main()
