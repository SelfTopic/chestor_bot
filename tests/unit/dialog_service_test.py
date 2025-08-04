import unittest
from unittest.mock import patch, mock_open, MagicMock

from src.bot.services import DialogService 


class TestDialogService(unittest.TestCase):

    @patch(
        "builtins.open", 
        new_callable=mock_open, 
        read_data='{ "start": "Hello!" }'
    )
    def test_init_default_name(self, mock_file: MagicMock):

        service = DialogService()

        mock_file.assert_called_with("dialogs.json", "r")

        self.assertEqual(service.cache, { "start": "Hello!" })

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{ "start": "Hello!" }'
    )
    def test_init_custom_name(self, mock_file: MagicMock): 

        service = DialogService("custom_dialogs_file.json")

        mock_file.assert_called_with("custom_dialogs_file.json", "r")

        self.assertEqual(service.cache, { "start": "Hello!" })

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{ "start": "Hello" }'
    )
    def test_text_key(self, mock_file: MagicMock):

        service = DialogService()

        text = service.text("start")

        self.assertEqual(text, "Hello")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{ "start": "Hello, {name}!" }'
    )
    def test_text_format_key(self, mock_file: MagicMock):

        service = DialogService()

        text = service.text("start")

        self.assertEqual(text, "Hello, {name}!")

        text = service.text("start", name="CheStor")

        self.assertEqual(text, "Hello, CheStor!")


if __name__ == '__main__':
    unittest.main()