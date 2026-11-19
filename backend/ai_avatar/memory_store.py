# ===============================================
# File: Pulsar/backend/ai_avatar/memory_store.py
#
# Description:
# Encrypted persistent storage for AI Avatar conversations and memory
#
# Change Date: 2026-10-16
# Timezone: Asia/Baku
#
# Author: MHKolahi@gmail.com
# In collaboration with GPT4 Chat Assistant: Bahram
# ===============================================

import base64
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AIAvatarMemoryError(Exception):
    """Represent a controlled encrypted-memory storage error."""


class AIAvatarMemoryStore:
    """Persist user-isolated AI Avatar history and encrypted memory."""

    NONCE_BYTES = 12
    TAG_BYTES = 16
    DEFAULT_KEY_VERSION = "v1"
    DEFAULT_KEY_REF = "AI_AVATAR_MEMORY_KEY"

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _uuid(value: Any, field_name: str) -> uuid.UUID:
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise AIAvatarMemoryError(
                f"Invalid {field_name}."
            ) from exc

    def _get_key(self) -> tuple[bytes, str, str]:
        """Load a 256-bit encryption key from the runtime environment."""

        key_ref = os.environ.get(
            "AI_AVATAR_MEMORY_KEY_REF",
            self.DEFAULT_KEY_REF,
        )
        encoded_key = os.environ.get(key_ref)

        if not encoded_key:
            raise AIAvatarMemoryError(
                "AI Avatar memory encryption is not configured."
            )

        try:
            key = base64.b64decode(encoded_key, validate=True)
        except (ValueError, TypeError) as exc:
            raise AIAvatarMemoryError(
                "AI Avatar memory encryption key is invalid."
            ) from exc

        if len(key) != 32:
            raise AIAvatarMemoryError(
                "AI Avatar memory encryption key must contain 32 bytes."
            )

        key_version = os.environ.get(
            "AI_AVATAR_MEMORY_KEY_VERSION",
            self.DEFAULT_KEY_VERSION,
        )

        return key, key_ref, key_version

    @staticmethod
    def _aad(
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        record_id: uuid.UUID,
        purpose: str,
    ) -> bytes:
        """Bind ciphertext to its owner and logical record."""

        return (
            f"pulsar-ai-avatar:v1:{purpose}:"
            f"{user_id}:{definition_id}:{record_id}"
        ).encode("utf-8")

    def _encrypt(
        self,
        content: str,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        record_id: uuid.UUID,
        purpose: str,
    ) -> dict[str, Any]:
        key, key_ref, key_version = self._get_key()
        nonce = os.urandom(self.NONCE_BYTES)
        encrypted = AESGCM(key).encrypt(
            nonce,
            content.encode("utf-8"),
            self._aad(user_id, definition_id, record_id, purpose),
        )

        return {
            "ciphertext": encrypted[:-self.TAG_BYTES],
            "nonce": nonce,
            "tag": encrypted[-self.TAG_BYTES:],
            "key_ref": key_ref,
            "key_version": key_version,
        }

    def _decrypt(
        self,
        ciphertext: bytes,
        nonce: bytes,
        tag: bytes,
        key_ref: str,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        record_id: uuid.UUID,
        purpose: str,
    ) -> str:
        """Decrypt only when the configured key and authenticated data match."""

        encoded_key = os.environ.get(key_ref)

        if not encoded_key:
            raise AIAvatarMemoryError(
                "The encryption key required for stored Avatar data is unavailable."
            )

        try:
            key = base64.b64decode(encoded_key, validate=True)

            if len(key) != 32:
                raise ValueError("Invalid key length.")

            plaintext = AESGCM(key).decrypt(
                nonce,
                ciphertext + tag,
                self._aad(user_id, definition_id, record_id, purpose),
            )
            return plaintext.decode("utf-8")

        except (ValueError, TypeError, InvalidTag, UnicodeDecodeError) as exc:
            raise AIAvatarMemoryError(
                "Stored Avatar data could not be authenticated or decrypted."
            ) from exc

    async def get_policy(
        self,
        definition_id: uuid.UUID,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            text("""
                SELECT
                    c_history_retention_days,
                    c_memory_retention_days,
                    c_max_history_messages,
                    c_max_memory_items,
                    c_max_memory_bytes
                FROM pulsar.t_ai_avatar_memory_policy
                WHERE c_ai_definition_id = :definition_id
                  AND upper(c_state) = 'ACTIVE'
                ORDER BY c_updated_at DESC
                LIMIT 1
            """),
            {"definition_id": definition_id},
        )
        row = result.mappings().first()

        if not row:
            raise AIAvatarMemoryError(
                "No active AI Avatar memory policy is configured."
            )

        policy = dict(row)

        for field in (
            "c_history_retention_days",
            "c_memory_retention_days",
            "c_max_history_messages",
            "c_max_memory_items",
            "c_max_memory_bytes",
        ):
            if int(policy[field]) <= 0:
                raise AIAvatarMemoryError(
                    "The active AI Avatar memory policy contains an invalid limit."
                )

        return policy

    async def cleanup_expired(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
    ) -> None:
        """Remove expired records without crossing user or Avatar boundaries."""

        parameters = {
            "user_id": user_id,
            "definition_id": definition_id,
        }

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_memory
                WHERE c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
                  AND c_expires_at <= CURRENT_TIMESTAMP
            """),
            parameters,
        )

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_message m
                USING pulsar.t_ai_avatar_conversation c
                WHERE m.c_conversation_id = c.c_conversation_id
                  AND m.c_user_id = :user_id
                  AND m.c_ai_definition_id = :definition_id
                  AND c.c_user_id = :user_id
                  AND c.c_ai_definition_id = :definition_id
                  AND (
                      c.c_expires_at <= CURRENT_TIMESTAMP
                      OR c.c_state <> 'active'
                  )
            """),
            parameters,
        )

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_conversation
                WHERE c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
                  AND (
                      c_expires_at <= CURRENT_TIMESTAMP
                      OR c_state <> 'active'
                  )
            """),
            parameters,
        )

    async def get_or_create_conversation(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        policy: dict[str, Any],
    ) -> uuid.UUID:
        """Return the user's most recent active conversation or create one."""

        result = await self.session.execute(
            text("""
                SELECT c_conversation_id
                FROM pulsar.t_ai_avatar_conversation
                WHERE c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
                  AND c_state = 'active'
                  AND c_expires_at > CURRENT_TIMESTAMP
                ORDER BY c_last_message_at DESC
                LIMIT 1
                FOR UPDATE
            """),
            {
                "user_id": user_id,
                "definition_id": definition_id,
            },
        )
        row = result.mappings().first()

        if row:
            return self._uuid(
                row["c_conversation_id"],
                "conversation ID",
            )

        conversation_id = uuid.uuid4()
        retention_days = int(policy["c_history_retention_days"])

        await self.session.execute(
            text("""
                INSERT INTO pulsar.t_ai_avatar_conversation (
                    c_conversation_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_state,
                    c_expires_at
                )
                VALUES (
                    :conversation_id,
                    :user_id,
                    :definition_id,
                    'active',
                    CURRENT_TIMESTAMP
                        + (:retention_days * INTERVAL '1 day')
                )
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "retention_days": retention_days,
            },
        )

        return conversation_id

    async def load_history(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        conversation_id: uuid.UUID,
        policy: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Load a bounded, decrypted history belonging to the authenticated owner."""

        result = await self.session.execute(
            text("""
                SELECT
                    m.c_message_id,
                    m.c_role,
                    m.c_content_ciphertext,
                    m.c_encryption_nonce,
                    m.c_encryption_tag,
                    m.c_encryption_key_ref
                FROM pulsar.t_ai_avatar_message m
                JOIN pulsar.t_ai_avatar_conversation c
                  ON c.c_conversation_id = m.c_conversation_id
                WHERE m.c_conversation_id = :conversation_id
                  AND m.c_user_id = :user_id
                  AND m.c_ai_definition_id = :definition_id
                  AND c.c_user_id = :user_id
                  AND c.c_ai_definition_id = :definition_id
                  AND c.c_state = 'active'
                  AND c.c_expires_at > CURRENT_TIMESTAMP
                ORDER BY m.c_created_at DESC
                LIMIT :max_messages
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "max_messages": int(policy["c_max_history_messages"]),
            },
        )

        rows = list(result.mappings().all())
        rows.reverse()
        messages = []

        for row in rows:
            role = row["c_role"]

            if role not in {"user", "assistant"}:
                continue

            message_id = self._uuid(row["c_message_id"], "message ID")
            content = self._decrypt(
                ciphertext=bytes(row["c_content_ciphertext"]),
                nonce=bytes(row["c_encryption_nonce"]),
                tag=bytes(row["c_encryption_tag"]),
                key_ref=row["c_encryption_key_ref"],
                user_id=user_id,
                definition_id=definition_id,
                record_id=message_id,
                purpose=f"message:{role}",
            )
            messages.append({"role": role, "content": content})

        return messages

    async def save_message(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        policy: dict[str, Any],
    ) -> uuid.UUID:
        """Encrypt and persist one message, then refresh conversation expiry."""

        if role not in {"user", "assistant"}:
            raise AIAvatarMemoryError("Unsupported conversation message role.")

        if not isinstance(content, str) or not content:
            raise AIAvatarMemoryError("Message content must not be empty.")

        if len(content.encode("utf-8")) > 1_000_000:
            raise AIAvatarMemoryError("Message exceeds the allowed size.")

        # Confirm ownership before inserting any message.
        result = await self.session.execute(
            text("""
                SELECT c_conversation_id
                FROM pulsar.t_ai_avatar_conversation
                WHERE c_conversation_id = :conversation_id
                  AND c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
                  AND c_state = 'active'
                  AND c_expires_at > CURRENT_TIMESTAMP
                FOR UPDATE
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
            },
        )

        if not result.mappings().first():
            raise AIAvatarMemoryError(
                "The requested Avatar conversation is unavailable."
            )

        message_id = uuid.uuid4()
        encrypted = self._encrypt(
            content=content,
            user_id=user_id,
            definition_id=definition_id,
            record_id=message_id,
            purpose=f"message:{role}",
        )

        await self.session.execute(
            text("""
                INSERT INTO pulsar.t_ai_avatar_message (
                    c_message_id,
                    c_conversation_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_role,
                    c_content_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref,
                    c_encryption_key_version
                )
                VALUES (
                    :message_id,
                    :conversation_id,
                    :user_id,
                    :definition_id,
                    :role,
                    :ciphertext,
                    :nonce,
                    :tag,
                    :key_ref,
                    :key_version
                )
            """),
            {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "role": role,
                **encrypted,
            },
        )

        await self.session.execute(
            text("""
                UPDATE pulsar.t_ai_avatar_conversation
                SET c_last_message_at = CURRENT_TIMESTAMP,
                    c_updated_at = CURRENT_TIMESTAMP,
                    c_expires_at = CURRENT_TIMESTAMP
                        + (:retention_days * INTERVAL '1 day')
                WHERE c_conversation_id = :conversation_id
                  AND c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "retention_days": int(policy["c_history_retention_days"]),
            },
        )

        return message_id

    async def save_memory(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        source_message_id: uuid.UUID,
        memory_type: str,
        content: str,
        policy: dict[str, Any],
    ) -> uuid.UUID:
        """Persist a separately encrypted long-term memory item."""

        if not isinstance(memory_type, str) or not memory_type.strip():
            raise AIAvatarMemoryError("Memory type is required.")

        if not isinstance(content, str) or not content.strip():
            raise AIAvatarMemoryError("Memory content must not be empty.")

        if len(content.encode("utf-8")) > int(policy["c_max_memory_bytes"]):
            raise AIAvatarMemoryError("Memory item exceeds the configured size limit.")

        source_result = await self.session.execute(
            text("""
                SELECT c_message_id
                FROM pulsar.t_ai_avatar_message
                WHERE c_message_id = :source_message_id
                  AND c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
            """),
            {
                "source_message_id": source_message_id,
                "user_id": user_id,
                "definition_id": definition_id,
            },
        )

        if not source_result.mappings().first():
            raise AIAvatarMemoryError(
                "The source message is not available to this user and Avatar."
            )

        memory_id = uuid.uuid4()
        encrypted = self._encrypt(
            content=content,
            user_id=user_id,
            definition_id=definition_id,
            record_id=memory_id,
            purpose=f"memory:{memory_type}",
        )

        await self.session.execute(
            text("""
                INSERT INTO pulsar.t_ai_avatar_memory (
                    c_memory_id,
                    c_user_id,
                    c_ai_definition_id,
                    c_source_message_id,
                    c_memory_type,
                    c_content_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref,
                    c_encryption_key_version,
                    c_expires_at
                )
                VALUES (
                    :memory_id,
                    :user_id,
                    :definition_id,
                    :source_message_id,
                    :memory_type,
                    :ciphertext,
                    :nonce,
                    :tag,
                    :key_ref,
                    :key_version,
                    CURRENT_TIMESTAMP
                        + (:retention_days * INTERVAL '1 day')
                )
            """),
            {
                "memory_id": memory_id,
                "user_id": user_id,
                "definition_id": definition_id,
                "source_message_id": source_message_id,
                "memory_type": memory_type,
                "retention_days": int(policy["c_memory_retention_days"]),
                **encrypted,
            },
        )

        await self.enforce_memory_limits(user_id, definition_id, policy)
        return memory_id

    async def enforce_memory_limits(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        policy: dict[str, Any],
    ) -> None:
        """Keep only the newest configured number of memory records."""

        await self.session.execute(
            text("""
                DELETE FROM pulsar.t_ai_avatar_memory m
                WHERE m.c_user_id = :user_id
                  AND m.c_ai_definition_id = :definition_id
                  AND m.c_memory_id IN (
                      SELECT c_memory_id
                      FROM pulsar.t_ai_avatar_memory
                      WHERE c_user_id = :user_id
                        AND c_ai_definition_id = :definition_id
                      ORDER BY c_created_at DESC, c_memory_id DESC
                      OFFSET :max_items
                  )
            """),
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "max_items": int(policy["c_max_memory_items"]),
            },
        )

    async def load_memories(
        self,
        user_id: uuid.UUID,
        definition_id: uuid.UUID,
        policy: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Load unexpired long-term memories for this user and Avatar only."""

        result = await self.session.execute(
            text("""
                SELECT
                    c_memory_id,
                    c_memory_type,
                    c_content_ciphertext,
                    c_encryption_nonce,
                    c_encryption_tag,
                    c_encryption_key_ref
                FROM pulsar.t_ai_avatar_memory
                WHERE c_user_id = :user_id
                  AND c_ai_definition_id = :definition_id
                  AND c_expires_at > CURRENT_TIMESTAMP
                ORDER BY c_created_at DESC
                LIMIT :max_items
            """),
            {
                "user_id": user_id,
                "definition_id": definition_id,
                "max_items": int(policy["c_max_memory_items"]),
            },
        )

        memories = []

        for row in result.mappings().all():
            memory_id = self._uuid(row["c_memory_id"], "memory ID")
            memory_type = row["c_memory_type"]
            content = self._decrypt(
                ciphertext=bytes(row["c_content_ciphertext"]),
                nonce=bytes(row["c_encryption_nonce"]),
                tag=bytes(row["c_encryption_tag"]),
                key_ref=row["c_encryption_key_ref"],
                user_id=user_id,
                definition_id=definition_id,
                record_id=memory_id,
                purpose=f"memory:{memory_type}",
            )
            memories.append({
                "memory_type": memory_type,
                "content": content,
            })

        return memories
