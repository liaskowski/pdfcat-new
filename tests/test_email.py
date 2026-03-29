import unittest
from unittest.mock import patch, MagicMock
from server.services.email_service import send_welcome_email, send_reset_email, _send_email

class TestEmailService(unittest.TestCase):
    @patch("smtplib.SMTP")
    def test_send_email_success(self, mock_smtp):
        # Setup mock
        instance = mock_smtp.return_value.__enter__.return_value
        
        # Test basic sending
        result = _send_email("test@example.com", "Subject", "<html>Body</html>")
        
        self.assertTrue(result)
        self.assertTrue(instance.send_message.called)
        self.assertTrue(instance.starttls.called)

    @patch("smtplib.SMTP")
    def test_send_email_failure(self, mock_smtp):
        # Setup mock to raise error
        instance = mock_smtp.return_value.__enter__.return_value
        instance.send_message.side_effect = Exception("SMTP Error")
        
        result = _send_email("test@example.com", "Subject", "<html>Body</html>")
        
        self.assertFalse(result)

    def test_send_email_no_recipient(self):
        result = _send_email("", "Subject", "<html>Body</html>")
        self.assertFalse(result)

    @patch("server.services.email_service._send_email")
    def test_welcome_email_content(self, mock_send):
        send_welcome_email("user@test.com", "testuser", "secret123")
        
        args, kwargs = mock_send.call_args
        self.assertEqual(args[0], "user@test.com")
        self.assertEqual(args[1], "Welcome to PDF Library")
        self.assertIn("testuser", args[2])
        self.assertIn("secret123", args[2])

if __name__ == "__main__":
    unittest.main()
