import base64
import io
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from line_art import ImageValidationError, GenerationError, prepare_image, generate_line_art, PROMPT


def image_bytes(fmt="PNG"):
    result = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(result, fmt)
    return result.getvalue()


class DemoTests(unittest.TestCase):
    def test_valid_jpg_and_png(self):
        for fmt in ("JPEG", "PNG"):
            result = prepare_image(image_bytes(fmt))
            with Image.open(io.BytesIO(result)) as img:
                self.assertEqual(img.format, "PNG")
                self.assertEqual(img.size, (40, 30))

    def test_invalid_uploads(self):
        for raw in (b"", b"not an image", image_bytes("GIF"), b"x" * (10*1024*1024+1)):
            with self.assertRaises(ImageValidationError):
                prepare_image(raw)

    def test_pixel_limit(self):
        with patch("line_art.MAX_PIXELS", 100):
            with self.assertRaises(ImageValidationError):
                prepare_image(image_bytes())

    @patch("line_art.OpenAI")
    def test_edit_contract_and_output(self, client):
        service = client.return_value.__enter__.return_value
        service.images.edit.return_value = SimpleNamespace(data=[SimpleNamespace(
            b64_json=base64.b64encode(image_bytes()).decode())])
        output = generate_line_art(image_bytes(), "test-key")
        args = service.images.edit.call_args.kwargs
        self.assertEqual(args["prompt"], PROMPT)
        self.assertEqual(args["image"][1], image_bytes())
        self.assertEqual(args["n"], 1)
        self.assertEqual(Image.open(io.BytesIO(output)).mode, "L")

    @patch("line_art.OpenAI")
    def test_empty_api_response(self, client):
        client.return_value.__enter__.return_value.images.edit.return_value = SimpleNamespace(data=[])
        with self.assertRaises(GenerationError):
            generate_line_art(image_bytes(), "test-key")

    def test_launch_without_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch("dotenv.load_dotenv"):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Setup needed" in item.value for item in app.info))
        self.assertTrue(app.button[0].disabled)
        self.assertEqual(app.button[0].label, "Generate Line Drawing")

    def test_upload_preview_result_and_reset(self):
        from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
        from streamlit.proto.Common_pb2 import FileURLs
        file = UploadedFile(UploadedFileRec("1", "sample.png", "image/png", image_bytes()), FileURLs())
        app_path = str(Path(__file__).resolve().parents[1] / "app.py")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch("dotenv.load_dotenv"), \
                patch("streamlit.file_uploader", return_value=file), \
                patch("line_art.generate_line_art", return_value=image_bytes()) as generate:
            app = AppTest.from_file(app_path).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.button[0].disabled)
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["result"], image_bytes())
            self.assertEqual(len(app.get("download_button")), 1)
            generate.assert_called_once()
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch("dotenv.load_dotenv"), \
                patch("streamlit.file_uploader", return_value=None):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
