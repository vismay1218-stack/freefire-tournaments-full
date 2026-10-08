import os
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename as _secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_MIME_PREFIXES = ("image/",)

_IMAGE_CONTENT_TYPES = {
    "gif": "image/gif",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _extension_ok(filename):
    if "." not in filename:
        return False, None
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS, ext


def secure_random_filename(ext):
    return f"{uuid.uuid4().hex}.{ext.lower().lstrip('.')}"


def validate_image(file_storage, max_size_bytes=None):
    errors = []
    if not file_storage or not file_storage.filename:
        errors.append("No file uploaded.")
        return errors, None
    filename = file_storage.filename
    ok_ext, ext = _extension_ok(filename)
    if not ok_ext:
        errors.append(
            f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )
        return errors, None
    if max_size_bytes:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
        if size > max_size_bytes:
            errors.append("File is too large.")
            return errors, None
    try:
        with Image.open(file_storage) as im:
            im.verify()
        file_storage.seek(0)
    except Exception:
        errors.append("Image is corrupted or not a real image.")
        return errors, None
    return errors, ext


def _storage_credentials(app_config):
    url = app_config.get("SUPABASE_URL")
    key = app_config.get("SUPABASE_SERVICE_ROLE_KEY")
    if bool(url) != bool(key):
        raise RuntimeError(
            "Both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )
    if not url:
        return None
    return url.rstrip("/"), key


def _storage_request(app_config, bucket, filename, method, data=None, content_type=None):
    credentials = _storage_credentials(app_config)
    if credentials is None:
        raise RuntimeError("Supabase Storage is not configured.")
    base_url, service_key = credentials
    object_path = quote(f"{bucket}/{filename}", safe="/")
    request = Request(
        f"{base_url}/storage/v1/object/{object_path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            **({"Content-Type": content_type} if content_type else {}),
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except HTTPError as error:
        if error.code == 404 and method == "GET":
            raise FileNotFoundError(filename) from error
        raise RuntimeError(
            f"Supabase Storage request failed with HTTP {error.code}."
        ) from error


def _valid_stored_filename(filename):
    return (
        bool(filename)
        and filename not in {".", ".."}
        and "/" not in filename
        and "\\" not in filename
        and Path(filename).name == filename
    )


def _save_to_folder(file_storage, folder, max_size_bytes, app_config, bucket):
    errs, ext = validate_image(file_storage, max_size_bytes)
    if errs:
        return None, errs

    filename = secure_random_filename(ext)
    credentials = _storage_credentials(app_config)
    if credentials:
        _storage_request(
            app_config,
            bucket,
            filename,
            "POST",
            data=file_storage.read(),
            content_type=_IMAGE_CONTENT_TYPES[ext],
        )
        return filename, []

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    safe = _secure_filename(filename) or filename
    target = folder / safe
    file_storage.save(str(target))
    return safe, []


def save_payment_screenshot(file_storage, app_config):
    return _save_to_folder(
        file_storage,
        app_config["PAYMENT_SCREENSHOTS_DIR"],
        app_config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024),
        app_config,
        app_config.get("SUPABASE_PAYMENT_BUCKET", "payment-screenshots"),
    )


def save_winner_image(file_storage, app_config):
    return _save_to_folder(
        file_storage,
        app_config["WINNERS_PUBLIC_DIR"],
        app_config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024),
        app_config,
        app_config.get("SUPABASE_WINNERS_BUCKET", "winner-images"),
    )


def load_stored_image(filename, app_config, *, purpose):
    if not _valid_stored_filename(filename):
        raise FileNotFoundError(filename)

    folder_key, bucket_key = {
        "payment": ("PAYMENT_SCREENSHOTS_DIR", "SUPABASE_PAYMENT_BUCKET"),
        "winner": ("WINNERS_PUBLIC_DIR", "SUPABASE_WINNERS_BUCKET"),
    }[purpose]
    credentials = _storage_credentials(app_config)
    if credentials:
        return _storage_request(
            app_config,
            app_config.get(bucket_key, "payment-screenshots" if purpose == "payment" else "winner-images"),
            filename,
            "GET",
        )

    return (Path(app_config[folder_key]) / filename).read_bytes()


def delete_stored_image(filename, app_config, *, purpose):
    if not _valid_stored_filename(filename):
        raise ValueError("Invalid stored image name.")

    folder_key, bucket_key = {
        "payment": ("PAYMENT_SCREENSHOTS_DIR", "SUPABASE_PAYMENT_BUCKET"),
        "winner": ("WINNERS_PUBLIC_DIR", "SUPABASE_WINNERS_BUCKET"),
    }[purpose]
    credentials = _storage_credentials(app_config)
    if credentials:
        _storage_request(
            app_config,
            app_config.get(bucket_key, "payment-screenshots" if purpose == "payment" else "winner-images"),
            filename,
            "DELETE",
        )
        return

    (Path(app_config[folder_key]) / filename).unlink(missing_ok=True)
