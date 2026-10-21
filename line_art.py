"""Image validation and the single-image OpenAI editing service."""
import base64
import binascii
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from openai import OpenAI

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
DEFAULT_MODEL = "gpt-image-1.5"
PROMPT = """Convert the supplied image into a clean black-and-white editorial line drawing.
Preserve the main subject, recognizable features, pose, proportions, composition,
and relative placement of objects. Use crisp black contours with consistent line
weight on a pure white background. Simplify background details. Use only essential
interior lines; no color, gray shading, gradients, hatching, textures or large solid
black fills. Do not invent objects, add text, borders or watermarks. Keep the entire
main subject visible. Produce one polished, uncluttered line-art image."""


class ImageValidationError(ValueError):
    pass


class GenerationError(RuntimeError):
    pass


def prepare_image(data: bytes) -> bytes:
    """Validate actual content; normalize orientation, transparency and metadata."""
    if not data:
        raise ImageValidationError("The file is empty. Choose a JPG or PNG image.")
    if len(data) > MAX_BYTES:
        raise ImageValidationError("Please choose an image smaller than 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG"}:
                    raise ImageValidationError("Only actual JPG and PNG images are supported.")
                if source.width * source.height > MAX_PIXELS:
                    raise ImageValidationError("Image is too large. Use an image under 25 megapixels.")
                if getattr(source, "n_frames", 1) > 1:
                    raise ImageValidationError("Please use a still image rather than an animated PNG.")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                result = io.BytesIO()
                background.save(result, format="PNG")
                return result.getvalue()
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ImageValidationError("This image cannot be read. Try exporting it again as JPG or PNG.") from exc


def generate_line_art(image: bytes, api_key: str, model: str = DEFAULT_MODEL) -> bytes:
    if not api_key.strip():
        raise GenerationError("Set OPENAI_API_KEY in your .env file and restart the app.")
    # Explicit retries prevent silent repeat generation requests after a timeout.
    with OpenAI(api_key=api_key, timeout=180.0, max_retries=0) as client:
        result = client.images.edit(
            model=model, image=("source.png", image, "image/png"),
            prompt=PROMPT, n=1, size="auto", quality="medium", output_format="png",
        )
    if not result.data or not result.data[0].b64_json:
        raise GenerationError("No image was returned. Please try another image.")
    try:
        decoded = base64.b64decode(result.data[0].b64_json, validate=True)
        with Image.open(io.BytesIO(decoded)) as generated:
            generated.load()
            # Guarantee a monochrome PNG even if the model introduces a color tint.
            output = io.BytesIO()
            rgba = generated.convert("RGBA")
            white = Image.new("RGBA", rgba.size, "white")
            white.alpha_composite(rgba)
            white.convert("L").save(output, "PNG")
            return output.getvalue()
    except (ValueError, binascii.Error, OSError) as exc:
        raise GenerationError("The service returned an unreadable image. Please try again.") from exc
