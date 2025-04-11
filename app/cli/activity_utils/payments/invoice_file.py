import io
from urllib.parse import urljoin

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.core.settings import AppSettings, get_settings
from app.models.product import ProductEnum


def normalise_http_url(url: str) -> str:
    """
    normalise url with http scheme
    """
    if not url.startswith("http"):
        url = "http://" + url  # NOSONAR
    if url.startswith("https://"):
        url = "http://" + url.removeprefix("https://")  # NOSONAR
    return url


def get_invoice_helper(product: ProductEnum, resp: dict) -> dict:
    """
    @param resp:
    @return:
    """
    app_config = ProductEnum.get_product_settings(product)
    config: AppSettings = get_settings()

    if resp.get("file_url"):
        # normalize file url
        file_url = normalise_http_url(str(resp["file_url"]))
        api_url = normalise_http_url(str(app_config.lago.api_url))

        if file_url.startswith(api_url):
            if api_url.endswith("/"):
                api_url = api_url.removesuffix("/")
            if file_url.startswith(api_url):
                resp["file_url"] = file_url.replace(api_url, urljoin(config.billing_url, "billing"))
    resp["external_id"] = resp.pop("lago_id")
    return resp


def is_valid_pdf(pdf_bytes: bytes) -> tuple[bool, str]:
    """
    Check bytes of file
    """
    pdf_stream = io.BytesIO(pdf_bytes)
    try:
        # Attempt to read the PDF content
        reader = PdfReader(pdf_stream)
    except PyPdfError as e:
        # If any error occurs, it's not a valid PDF
        return False, f"Error reading file: {e!r}"

    pages = len(reader.pages)
    if pages < 1:
        return False, "No pages found in the file!"

    return True, ""
