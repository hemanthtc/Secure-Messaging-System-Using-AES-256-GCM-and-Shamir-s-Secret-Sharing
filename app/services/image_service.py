"""
Image Service Module
Handles secure image upload, storage, access control, and 7-day retention auto-purge.
Images are stored outside static/executable directories with random unguessable IDs.
Authorization is strictly checked on every image access request.
"""

import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from app.database.db import mongo
from app.models.conversation import Conversation
from app.models.user import User

# Allowed formats and max size
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
RETENTION_DAYS = 7

# Signatures (Magic Bytes) for image format validation
IMAGE_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",
}

class ImageService:
    """Service managing secure image uploads, retrieval, and 7-day retention."""

    @staticmethod
    def get_upload_dir() -> Path:
        """Resolve and ensure the private uploads directory exists."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        upload_dir = base_dir / "instance" / "uploads" / "images"
        upload_dir.mkdir(parents=True, exist_ok=True)
        return upload_dir

    @staticmethod
    def validate_image_bytes(raw_bytes: bytes, original_filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate file size, extension, and binary magic bytes.
        Returns (is_valid, mime_type, error_message).
        """
        if not raw_bytes:
            return False, None, "Uploaded file is empty."

        if len(raw_bytes) > MAX_IMAGE_BYTES:
            return False, None, f"Image size exceeds 5MB limit ({len(raw_bytes)} bytes)."

        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, None, f"Disallowed file extension '{ext}'. Permitted: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

        # Verify magic bytes
        detected_mime = None
        for magic, mime in IMAGE_MAGIC_BYTES.items():
            if raw_bytes.startswith(magic):
                detected_mime = mime
                break

        # Special check for WEBP (starts with RIFF....WEBP)
        if raw_bytes[:4] == b"RIFF" and len(raw_bytes) >= 12 and raw_bytes[8:12] == b"WEBP":
            detected_mime = "image/webp"

        if not detected_mime or detected_mime not in ALLOWED_MIME_TYPES:
            return False, None, "File content is not a recognized valid image format."

        return True, detected_mime, None

    @staticmethod
    def save_image(
        raw_bytes: bytes,
        original_filename: str,
        conversation_id: str,
        uploader: User
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate and save an image.
        Assigns a random unguessable storage identifier and 7-day expiration timestamp.
        """
        conv = Conversation.find_by_id(conversation_id)
        if not conv or uploader.internal_id not in conv.participants:
            return None, "Unauthorized conversation access."

        is_valid, mime_type, err = ImageService.validate_image_bytes(raw_bytes, original_filename)
        if not is_valid:
            return None, err

        ext = Path(original_filename).suffix.lower()
        if ext == ".jpeg":
            ext = ".jpg"

        image_id = secrets.token_hex(16)
        storage_filename = f"{image_id}{ext}"
        upload_dir = ImageService.get_upload_dir()
        file_path = upload_dir / storage_filename

        # Write safely to disk
        try:
            with open(file_path, "wb") as f:
                f.write(raw_bytes)
        except Exception as e:
            return None, f"Failed to persist image to disk: {str(e)}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=RETENTION_DAYS)

        image_doc = {
            "image_id": image_id,
            "conversation_id": conversation_id,
            "uploaded_by_id": uploader.internal_id,
            "original_filename": Path(original_filename).name[:100],
            "storage_filename": storage_filename,
            "mime_type": mime_type,
            "file_size": len(raw_bytes),
            "uploaded_at": now,
            "expires_at": expires_at,
            "is_expired": False,
        }

        mongo.db.images.insert_one(image_doc)

        return {
            "image_id": image_id,
            "original_filename": image_doc["original_filename"],
            "mime_type": mime_type,
            "file_size": len(raw_bytes),
            "expires_at": expires_at.isoformat(),
        }, None

    @staticmethod
    def get_authorized_image(image_id: str, requesting_user: User) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
        """
        Retrieve image path and MIME type if user is authorized.
        Enforces 7-day expiration check.
        """
        if not image_id or not requesting_user:
            return None, None, "Invalid request."

        doc = mongo.db.images.find_one({"image_id": image_id})
        if not doc:
            return None, None, "Image not found."

        # Check conversation authorization
        conv = Conversation.find_by_id(doc["conversation_id"])
        if not conv or requesting_user.internal_id not in conv.participants:
            return None, None, "Unauthorized access to image."

        # Check if requesting user has deleted this message for themselves
        msg_doc = mongo.messages.find_one({"image_id": image_id})
        if msg_doc and requesting_user.internal_id in msg_doc.get("deleted_for", []):
            return None, None, "This image was deleted from your chat."

        # Check 7-day retention expiration
        now = datetime.now(timezone.utc)
        expires_at = doc.get("expires_at")
        if expires_at and isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at:
                doc["is_expired"] = True

        if doc.get("is_expired"):
            # Mark expired and delete file
            ImageService.delete_image_file(doc)
            return None, None, "This image has expired per the 7-day retention policy and was permanently deleted."

        upload_dir = ImageService.get_upload_dir()
        file_path = upload_dir / doc["storage_filename"]

        if not file_path.exists():
            return None, None, "Image file not found on disk."

        return file_path, doc.get("mime_type", "application/octet-stream"), None

    @staticmethod
    def delete_image_file(doc: dict):
        """Remove image file from disk and mark expired in database."""
        upload_dir = ImageService.get_upload_dir()
        file_path = upload_dir / doc.get("storage_filename", "")
        if file_path.exists():
            try:
                os.remove(file_path)
            except OSError:
                pass

        mongo.db.images.update_one(
            {"image_id": doc["image_id"]},
            {"$set": {"is_expired": True, "file_deleted_at": datetime.now(timezone.utc)}}
        )

    @staticmethod
    def delete_image_by_id(image_id: str):
        """Hard delete image file from disk and database record upon message deletion."""
        if not image_id:
            return
        doc = mongo.images.find_one({"image_id": image_id})
        if doc:
            upload_dir = ImageService.get_upload_dir()
            file_path = upload_dir / doc.get("storage_filename", "")
            if file_path.exists():
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            mongo.images.delete_one({"image_id": image_id})

    @staticmethod
    def purge_expired_images() -> int:
        """
        Purge all images older than 7 days permanently from disk and database.
        Returns count of purged images.
        """
        now = datetime.now(timezone.utc)
        cursor = mongo.db.images.find({
            "$or": [
                {"expires_at": {"$lte": now}},
                {"expires_at": {"$lte": now.replace(tzinfo=None)}},
                {"is_expired": True}
            ]
        })
        purged_count = 0
        for doc in cursor:
            ImageService.delete_image_file(doc)
            purged_count += 1
        return purged_count
