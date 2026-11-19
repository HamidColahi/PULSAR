--
-- PostgreSQL database dump
--

-- Dumped from database version 14.18 (Homebrew)
-- Dumped by pg_dump version 14.18 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: t_ai_avatar_assignment; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_avatar_assignment (
    c_assignment_id uuid NOT NULL,
    c_user_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_state character varying(10) DEFAULT 'active'::character varying NOT NULL,
    c_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_introduction_shown_at timestamp with time zone,
    CONSTRAINT ck_ai_avatar_assignment_state CHECK (((c_state)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying])::text[])))
);


--
-- Name: COLUMN t_ai_avatar_assignment.c_assignment_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_assignment_id IS 'Unique avatar assignment identifier.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_user_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_user_id IS 'Owner user identifier.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_ai_definition_id IS 'Assigned AI definition identifier.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_state IS 'Assignment lifecycle state.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_created_at IS 'Assignment creation timestamp.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_updated_at IS 'Last assignment update timestamp.';


--
-- Name: COLUMN t_ai_avatar_assignment.c_introduction_shown_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_assignment.c_introduction_shown_at IS 'Timestamp when the first-introduction message was delivered to this user for this Avatar.';


--
-- Name: t_ai_avatar_conversation; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_avatar_conversation (
    c_conversation_id uuid NOT NULL,
    c_user_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_state character varying(10) DEFAULT 'active'::character varying NOT NULL,
    c_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_last_message_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_expires_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ai_avatar_conversation_state CHECK (((c_state)::text = ANY ((ARRAY['active'::character varying, 'archived'::character varying])::text[])))
);


--
-- Name: COLUMN t_ai_avatar_conversation.c_conversation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_conversation_id IS 'Unique conversation identifier.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_user_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_user_id IS 'Conversation owner user identifier.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_ai_definition_id IS 'Conversation AI definition identifier.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_state IS 'Conversation lifecycle state.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_created_at IS 'Conversation creation timestamp.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_updated_at IS 'Last conversation update timestamp.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_last_message_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_last_message_at IS 'Timestamp of the latest conversation activity.';


--
-- Name: COLUMN t_ai_avatar_conversation.c_expires_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_conversation.c_expires_at IS 'Conversation expiration timestamp.';


--
-- Name: t_ai_avatar_memory; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_avatar_memory (
    c_memory_id uuid NOT NULL,
    c_user_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_source_message_id uuid NOT NULL,
    c_memory_type character varying(30) NOT NULL,
    c_content_ciphertext bytea NOT NULL,
    c_encryption_nonce bytea NOT NULL,
    c_encryption_tag bytea NOT NULL,
    c_encryption_key_ref character varying(255) NOT NULL,
    c_encryption_key_version character varying(100) NOT NULL,
    c_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_expires_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_ai_avatar_memory_ciphertext CHECK ((octet_length(c_content_ciphertext) > 0)),
    CONSTRAINT ck_ai_avatar_memory_nonce CHECK ((octet_length(c_encryption_nonce) = 12)),
    CONSTRAINT ck_ai_avatar_memory_tag CHECK ((octet_length(c_encryption_tag) = 16))
);


--
-- Name: COLUMN t_ai_avatar_memory.c_memory_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_memory_id IS 'Unique long-term memory identifier.';


--
-- Name: COLUMN t_ai_avatar_memory.c_user_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_user_id IS 'Memory owner user identifier.';


--
-- Name: COLUMN t_ai_avatar_memory.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_ai_definition_id IS 'Memory AI definition identifier.';


--
-- Name: COLUMN t_ai_avatar_memory.c_source_message_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_source_message_id IS 'Source message identifier.';


--
-- Name: COLUMN t_ai_avatar_memory.c_memory_type; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_memory_type IS 'Long-term memory category.';


--
-- Name: COLUMN t_ai_avatar_memory.c_content_ciphertext; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_content_ciphertext IS 'Encrypted memory content.';


--
-- Name: COLUMN t_ai_avatar_memory.c_encryption_nonce; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_encryption_nonce IS 'Authenticated encryption nonce.';


--
-- Name: COLUMN t_ai_avatar_memory.c_encryption_tag; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_encryption_tag IS 'Authenticated encryption tag.';


--
-- Name: COLUMN t_ai_avatar_memory.c_encryption_key_ref; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_encryption_key_ref IS 'External encryption key reference.';


--
-- Name: COLUMN t_ai_avatar_memory.c_encryption_key_version; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_encryption_key_version IS 'Encryption key version identifier.';


--
-- Name: COLUMN t_ai_avatar_memory.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_created_at IS 'Memory creation timestamp.';


--
-- Name: COLUMN t_ai_avatar_memory.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_updated_at IS 'Last memory update timestamp.';


--
-- Name: COLUMN t_ai_avatar_memory.c_expires_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory.c_expires_at IS 'Memory expiration timestamp.';


--
-- Name: t_ai_avatar_memory_policy; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_avatar_memory_policy (
    c_policy_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_history_retention_days integer DEFAULT 90 NOT NULL,
    c_memory_retention_days integer DEFAULT 365 NOT NULL,
    c_max_history_messages integer DEFAULT 500 NOT NULL,
    c_max_memory_items integer DEFAULT 200 NOT NULL,
    c_max_memory_bytes bigint DEFAULT 2097152 NOT NULL,
    c_state character varying(10) DEFAULT 'active'::character varying NOT NULL,
    c_updated_by uuid,
    c_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_ai_avatar_policy_history_capacity CHECK (((c_max_history_messages >= 1) AND (c_max_history_messages <= 100000))),
    CONSTRAINT ck_ai_avatar_policy_history_retention CHECK (((c_history_retention_days >= 1) AND (c_history_retention_days <= 36500))),
    CONSTRAINT ck_ai_avatar_policy_memory_bytes CHECK (((c_max_memory_bytes >= 1024) AND (c_max_memory_bytes <= 1073741824))),
    CONSTRAINT ck_ai_avatar_policy_memory_capacity CHECK (((c_max_memory_items >= 1) AND (c_max_memory_items <= 100000))),
    CONSTRAINT ck_ai_avatar_policy_memory_retention CHECK (((c_memory_retention_days >= 1) AND (c_memory_retention_days <= 36500))),
    CONSTRAINT ck_ai_avatar_policy_state CHECK (((c_state)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying])::text[])))
);


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_policy_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_policy_id IS 'Unique memory policy identifier.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_ai_definition_id IS 'AI definition governed by this policy.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_history_retention_days; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_history_retention_days IS 'Conversation history retention period in days.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_memory_retention_days; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_memory_retention_days IS 'Long-term memory retention period in days.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_max_history_messages; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_max_history_messages IS 'Maximum retained history messages.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_max_memory_items; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_max_memory_items IS 'Maximum retained memory items.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_max_memory_bytes; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_max_memory_bytes IS 'Maximum retained encrypted memory size in bytes.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_state IS 'Memory policy lifecycle state.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_updated_by; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_updated_by IS 'User who last updated the policy.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_created_at IS 'Policy creation timestamp.';


--
-- Name: COLUMN t_ai_avatar_memory_policy.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_memory_policy.c_updated_at IS 'Last policy update timestamp.';


--
-- Name: t_ai_avatar_message; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_avatar_message (
    c_message_id uuid NOT NULL,
    c_conversation_id uuid NOT NULL,
    c_user_id uuid NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_role character varying(10) NOT NULL,
    c_content_ciphertext bytea NOT NULL,
    c_encryption_nonce bytea NOT NULL,
    c_encryption_tag bytea NOT NULL,
    c_encryption_key_ref character varying(255) NOT NULL,
    c_encryption_key_version character varying(100) NOT NULL,
    c_created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_ai_avatar_message_ciphertext CHECK ((octet_length(c_content_ciphertext) > 0)),
    CONSTRAINT ck_ai_avatar_message_nonce CHECK ((octet_length(c_encryption_nonce) = 12)),
    CONSTRAINT ck_ai_avatar_message_role CHECK (((c_role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying])::text[]))),
    CONSTRAINT ck_ai_avatar_message_tag CHECK ((octet_length(c_encryption_tag) = 16))
);


--
-- Name: COLUMN t_ai_avatar_message.c_message_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_message_id IS 'Unique message identifier.';


--
-- Name: COLUMN t_ai_avatar_message.c_conversation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_conversation_id IS 'Parent conversation identifier.';


--
-- Name: COLUMN t_ai_avatar_message.c_user_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_user_id IS 'Message owner user identifier.';


--
-- Name: COLUMN t_ai_avatar_message.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_ai_definition_id IS 'Message AI definition identifier.';


--
-- Name: COLUMN t_ai_avatar_message.c_role; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_role IS 'Message sender role.';


--
-- Name: COLUMN t_ai_avatar_message.c_content_ciphertext; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_content_ciphertext IS 'Encrypted message content.';


--
-- Name: COLUMN t_ai_avatar_message.c_encryption_nonce; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_encryption_nonce IS 'Authenticated encryption nonce.';


--
-- Name: COLUMN t_ai_avatar_message.c_encryption_tag; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_encryption_tag IS 'Authenticated encryption tag.';


--
-- Name: COLUMN t_ai_avatar_message.c_encryption_key_ref; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_encryption_key_ref IS 'External encryption key reference.';


--
-- Name: COLUMN t_ai_avatar_message.c_encryption_key_version; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_encryption_key_version IS 'Encryption key version identifier.';


--
-- Name: COLUMN t_ai_avatar_message.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_avatar_message.c_created_at IS 'Message creation timestamp.';


--
-- Name: t_ai_context; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_context (
    c_ai_context_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_context_code character varying(100) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_context_type character varying(50) NOT NULL,
    c_definition jsonb DEFAULT '{}'::jsonb NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_context_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_context_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_context; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_context IS 'AI Context Definition / تعریف Context هوش مصنوعی';


--
-- Name: COLUMN t_ai_context.c_ai_context_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_ai_context_id IS 'AI Context Identifier / شناسه Context';


--
-- Name: COLUMN t_ai_context.c_context_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_context_code IS 'Unique Context Code / کد یکتای Context';


--
-- Name: COLUMN t_ai_context.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_title IS 'Context Title / عنوان Context';


--
-- Name: COLUMN t_ai_context.c_context_type; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_context_type IS 'Context Type / نوع Context';


--
-- Name: COLUMN t_ai_context.c_definition; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_definition IS 'Context Metadata Definition / تعریف Metadata مربوط به Context';


--
-- Name: COLUMN t_ai_context.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_priority IS 'Context Priority / اولویت Context';


--
-- Name: COLUMN t_ai_context.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_context.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_definition; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition (
    c_ai_definition_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_definition_code character varying(100) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_description text,
    c_default_language character varying(20),
    c_enabled boolean DEFAULT true NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    c_introduction_enabled boolean DEFAULT true NOT NULL,
    c_introduction_translation_key character varying(100) DEFAULT 'AI_AVATAR_INTRODUCTION'::character varying NOT NULL,
    CONSTRAINT ck_t_ai_definition_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition IS 'AI Definition / تعریف قابلیت هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_definition_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_definition_code IS 'Unique AI Definition Code / کد یکتای تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_title IS 'AI Definition Title / عنوان تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_description; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_description IS 'AI Definition Description / شرح تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_default_language; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_default_language IS 'Default Language / زبان پیش‌فرض';


--
-- Name: COLUMN t_ai_definition.c_enabled; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_enabled IS 'Enable AI Definition / فعال بودن تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: COLUMN t_ai_definition.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_created_at IS 'Creation Timestamp / زمان ایجاد';


--
-- Name: COLUMN t_ai_definition.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_updated_at IS 'Last Update Timestamp / زمان آخرین بروزرسانی';


--
-- Name: COLUMN t_ai_definition.c_introduction_enabled; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_introduction_enabled IS 'Controls whether the Avatar introduces itself to each user on their first visit.';


--
-- Name: COLUMN t_ai_definition.c_introduction_translation_key; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition.c_introduction_translation_key IS 'Translation dictionary key for the Avatar first-introduction message.';


--
-- Name: t_ai_definition_context; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition_context (
    c_ai_definition_context_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_ai_context_id uuid NOT NULL,
    c_required boolean DEFAULT false NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_t_ai_definition_context_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_definition_context_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition_context; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition_context IS 'AI Definition to Context Mapping / ارتباط تعریف هوش مصنوعی با Context';


--
-- Name: COLUMN t_ai_definition_context.c_ai_definition_context_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_ai_definition_context_id IS 'Mapping Identifier / شناسه ارتباط';


--
-- Name: COLUMN t_ai_definition_context.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_context.c_ai_context_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_ai_context_id IS 'AI Context Identifier / شناسه Context';


--
-- Name: COLUMN t_ai_definition_context.c_required; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_required IS 'Required Context Flag / مشخص‌کننده اجباری بودن Context';


--
-- Name: COLUMN t_ai_definition_context.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_priority IS 'Context Priority / اولویت Context';


--
-- Name: COLUMN t_ai_definition_context.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_context.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_definition_model; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition_model (
    c_ai_definition_model_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_ai_model_id uuid NOT NULL,
    c_is_default boolean DEFAULT false NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_t_ai_definition_model_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_definition_model_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition_model; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition_model IS 'AI Definition to Model Mapping / ارتباط تعریف هوش مصنوعی با مدل';


--
-- Name: COLUMN t_ai_definition_model.c_ai_definition_model_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_ai_definition_model_id IS 'Mapping Identifier / شناسه ارتباط';


--
-- Name: COLUMN t_ai_definition_model.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_model.c_ai_model_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_ai_model_id IS 'AI Model Identifier / شناسه مدل هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_model.c_is_default; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_is_default IS 'Default Model Flag / مشخص‌کننده مدل پیش‌فرض';


--
-- Name: COLUMN t_ai_definition_model.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_priority IS 'Model Priority / اولویت مدل';


--
-- Name: COLUMN t_ai_definition_model.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_model.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_definition_operation; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition_operation (
    c_ai_definition_operation_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_ai_operation_id uuid NOT NULL,
    c_is_default boolean DEFAULT false NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_t_ai_definition_operation_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_definition_operation_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition_operation; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition_operation IS 'AI Definition to Operation Mapping / ارتباط تعریف هوش مصنوعی با عملیات';


--
-- Name: COLUMN t_ai_definition_operation.c_ai_definition_operation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_ai_definition_operation_id IS 'Mapping Identifier / شناسه ارتباط';


--
-- Name: COLUMN t_ai_definition_operation.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_operation.c_ai_operation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_ai_operation_id IS 'AI Operation Identifier / شناسه عملیات هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_operation.c_is_default; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_is_default IS 'Default Operation Flag / مشخص‌کننده عملیات پیش‌فرض';


--
-- Name: COLUMN t_ai_definition_operation.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_priority IS 'Operation Priority / اولویت عملیات';


--
-- Name: COLUMN t_ai_definition_operation.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_operation.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_definition_policy; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition_policy (
    c_ai_definition_policy_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_ai_policy_id uuid NOT NULL,
    c_required boolean DEFAULT false NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_t_ai_definition_policy_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_definition_policy_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition_policy; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition_policy IS 'AI Definition to Policy Mapping / ارتباط تعریف هوش مصنوعی با Policy';


--
-- Name: COLUMN t_ai_definition_policy.c_ai_definition_policy_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_ai_definition_policy_id IS 'Mapping Identifier / شناسه ارتباط';


--
-- Name: COLUMN t_ai_definition_policy.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_policy.c_ai_policy_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_ai_policy_id IS 'AI Policy Identifier / شناسه Policy';


--
-- Name: COLUMN t_ai_definition_policy.c_required; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_required IS 'Required Policy Flag / مشخص‌کننده اجباری بودن Policy';


--
-- Name: COLUMN t_ai_definition_policy.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_priority IS 'Policy Priority / اولویت Policy';


--
-- Name: COLUMN t_ai_definition_policy.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_policy.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_definition_presentation; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_definition_presentation (
    c_ai_definition_presentation_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_definition_id uuid NOT NULL,
    c_ai_presentation_id uuid NOT NULL,
    c_is_default boolean DEFAULT false NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_t_ai_definition_presentation_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_definition_presentation_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_definition_presentation; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_definition_presentation IS 'AI Definition to Presentation Mapping / ارتباط تعریف هوش مصنوعی با Presentation';


--
-- Name: COLUMN t_ai_definition_presentation.c_ai_definition_presentation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_ai_definition_presentation_id IS 'Mapping Identifier / شناسه ارتباط';


--
-- Name: COLUMN t_ai_definition_presentation.c_ai_definition_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_ai_definition_id IS 'AI Definition Identifier / شناسه تعریف هوش مصنوعی';


--
-- Name: COLUMN t_ai_definition_presentation.c_ai_presentation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_ai_presentation_id IS 'AI Presentation Identifier / شناسه Presentation';


--
-- Name: COLUMN t_ai_definition_presentation.c_is_default; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_is_default IS 'Default Presentation Flag / مشخص‌کننده Presentation پیش‌فرض';


--
-- Name: COLUMN t_ai_definition_presentation.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_priority IS 'Presentation Priority / اولویت Presentation';


--
-- Name: COLUMN t_ai_definition_presentation.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_definition_presentation.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_model; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_model (
    c_ai_model_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_provider_id uuid NOT NULL,
    c_model_code character varying(200) NOT NULL,
    c_model_name character varying(300) NOT NULL,
    c_title character varying(300),
    c_description text,
    c_input_enabled boolean DEFAULT true NOT NULL,
    c_output_enabled boolean DEFAULT true NOT NULL,
    c_tool_calling_enabled boolean DEFAULT false NOT NULL,
    c_context_window integer,
    c_parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_model_context CHECK (((c_context_window IS NULL) OR (c_context_window > 0))),
    CONSTRAINT ck_t_ai_model_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_model; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_model IS 'AI Model Metadata / متادیتای مدل هوش مصنوعی';


--
-- Name: COLUMN t_ai_model.c_ai_model_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_ai_model_id IS 'AI Model Identifier / شناسه مدل هوش مصنوعی';


--
-- Name: COLUMN t_ai_model.c_ai_provider_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_ai_provider_id IS 'AI Provider Identifier / شناسه ارائه‌دهنده هوش مصنوعی';


--
-- Name: COLUMN t_ai_model.c_model_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_model_code IS 'Provider Model Code / کد مدل نزد ارائه‌دهنده';


--
-- Name: COLUMN t_ai_model.c_model_name; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_model_name IS 'Model Name / نام مدل';


--
-- Name: COLUMN t_ai_model.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_title IS 'Model Title / عنوان مدل';


--
-- Name: COLUMN t_ai_model.c_description; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_description IS 'Model Description / شرح مدل';


--
-- Name: COLUMN t_ai_model.c_input_enabled; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_input_enabled IS 'Input Capability / قابلیت دریافت ورودی';


--
-- Name: COLUMN t_ai_model.c_output_enabled; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_output_enabled IS 'Output Capability / قابلیت تولید خروجی';


--
-- Name: COLUMN t_ai_model.c_tool_calling_enabled; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_tool_calling_enabled IS 'Tool Calling Capability / قابلیت فراخوانی ابزار';


--
-- Name: COLUMN t_ai_model.c_context_window; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_context_window IS 'Context Window Size / اندازه پنجره زمینه';


--
-- Name: COLUMN t_ai_model.c_parameters; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_parameters IS 'Default Model Parameters / پارامترهای پیش‌فرض مدل';


--
-- Name: COLUMN t_ai_model.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_state IS 'Model State / وضعیت مدل';


--
-- Name: COLUMN t_ai_model.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_created_at IS 'Creation Time / زمان ایجاد';


--
-- Name: COLUMN t_ai_model.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_model.c_updated_at IS 'Last Update Time / زمان آخرین تغییر';


--
-- Name: t_ai_operation; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_operation (
    c_ai_operation_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_ai_model_id uuid NOT NULL,
    c_operation_code character varying(150) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_system_prompt text NOT NULL,
    c_user_prompt_template text,
    c_output_schema jsonb,
    c_parameters jsonb DEFAULT '{}'::jsonb NOT NULL,
    c_description text,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_operation_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_operation; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_operation IS 'AI Operation Metadata / متادیتای عملیات هوش مصنوعی';


--
-- Name: COLUMN t_ai_operation.c_ai_operation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_ai_operation_id IS 'AI Operation Identifier / شناسه عملیات هوش مصنوعی';


--
-- Name: COLUMN t_ai_operation.c_ai_model_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_ai_model_id IS 'AI Model Identifier / شناسه مدل هوش مصنوعی';


--
-- Name: COLUMN t_ai_operation.c_operation_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_operation_code IS 'Operation Code / کد عملیات';


--
-- Name: COLUMN t_ai_operation.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_title IS 'Operation Title / عنوان عملیات';


--
-- Name: COLUMN t_ai_operation.c_system_prompt; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_system_prompt IS 'System Prompt / پرامپت سیستمی';


--
-- Name: COLUMN t_ai_operation.c_user_prompt_template; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_user_prompt_template IS 'User Prompt Template / قالب پرامپت کاربر';


--
-- Name: COLUMN t_ai_operation.c_output_schema; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_output_schema IS 'Structured Output Schema / ساختار خروجی ساختاریافته';


--
-- Name: COLUMN t_ai_operation.c_parameters; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_parameters IS 'Operation Parameters / پارامترهای عملیات';


--
-- Name: COLUMN t_ai_operation.c_description; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_description IS 'Operation Description / شرح عملیات';


--
-- Name: COLUMN t_ai_operation.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_state IS 'Operation State / وضعیت عملیات';


--
-- Name: COLUMN t_ai_operation.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_created_at IS 'Creation Time / زمان ایجاد';


--
-- Name: COLUMN t_ai_operation.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_operation.c_updated_at IS 'Last Update Time / زمان آخرین تغییر';


--
-- Name: t_ai_policy; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_policy (
    c_ai_policy_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_policy_code character varying(100) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_policy_type character varying(50) NOT NULL,
    c_definition jsonb DEFAULT '{}'::jsonb NOT NULL,
    c_priority integer DEFAULT 1 NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_policy_priority CHECK ((c_priority > 0)),
    CONSTRAINT ck_t_ai_policy_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_policy; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_policy IS 'AI Policy Definition / تعریف Policy هوش مصنوعی';


--
-- Name: COLUMN t_ai_policy.c_ai_policy_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_ai_policy_id IS 'AI Policy Identifier / شناسه Policy';


--
-- Name: COLUMN t_ai_policy.c_policy_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_policy_code IS 'Unique Policy Code / کد یکتای Policy';


--
-- Name: COLUMN t_ai_policy.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_title IS 'Policy Title / عنوان Policy';


--
-- Name: COLUMN t_ai_policy.c_policy_type; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_policy_type IS 'Policy Type / نوع Policy';


--
-- Name: COLUMN t_ai_policy.c_definition; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_definition IS 'Policy Metadata Definition / تعریف Metadata مربوط به Policy';


--
-- Name: COLUMN t_ai_policy.c_priority; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_priority IS 'Policy Priority / اولویت Policy';


--
-- Name: COLUMN t_ai_policy.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_policy.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_presentation; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_presentation (
    c_ai_presentation_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_presentation_code character varying(100) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_presentation_type character varying(50) NOT NULL,
    c_definition jsonb DEFAULT '{}'::jsonb NOT NULL,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_presentation_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_presentation; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_presentation IS 'AI Presentation Definition / تعریف Presentation هوش مصنوعی';


--
-- Name: COLUMN t_ai_presentation.c_ai_presentation_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_ai_presentation_id IS 'AI Presentation Identifier / شناسه Presentation';


--
-- Name: COLUMN t_ai_presentation.c_presentation_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_presentation_code IS 'Unique Presentation Code / کد یکتای Presentation';


--
-- Name: COLUMN t_ai_presentation.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_title IS 'Presentation Title / عنوان Presentation';


--
-- Name: COLUMN t_ai_presentation.c_presentation_type; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_presentation_type IS 'Presentation Type / نوع Presentation';


--
-- Name: COLUMN t_ai_presentation.c_definition; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_definition IS 'Presentation Metadata Definition / تعریف Metadata مربوط به Presentation';


--
-- Name: COLUMN t_ai_presentation.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_presentation.c_state IS 'Record State / وضعیت رکورد';


--
-- Name: t_ai_provider; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_ai_provider (
    c_ai_provider_id uuid DEFAULT gen_random_uuid() NOT NULL,
    c_provider_code character varying(100) NOT NULL,
    c_title character varying(300) NOT NULL,
    c_api_base_url text,
    c_api_key_ref character varying(500),
    c_description text,
    c_state character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    c_created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    c_avatar_manager_id bigint DEFAULT '3'::bigint NOT NULL,
    CONSTRAINT ck_t_ai_provider_state CHECK (((c_state)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: TABLE t_ai_provider; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_ai_provider IS 'AI Provider Metadata / متادیتای ارائه‌دهنده هوش مصنوعی';


--
-- Name: COLUMN t_ai_provider.c_ai_provider_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_ai_provider_id IS 'AI Provider Identifier / شناسه ارائه‌دهنده هوش مصنوعی';


--
-- Name: COLUMN t_ai_provider.c_provider_code; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_provider_code IS 'Provider Code / کد ارائه‌دهنده';


--
-- Name: COLUMN t_ai_provider.c_title; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_title IS 'Provider Title / عنوان ارائه‌دهنده';


--
-- Name: COLUMN t_ai_provider.c_api_base_url; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_api_base_url IS 'API Base URL / نشانی پایه API';


--
-- Name: COLUMN t_ai_provider.c_api_key_ref; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_api_key_ref IS 'API Key Secret Reference / مرجع Secret کلید API';


--
-- Name: COLUMN t_ai_provider.c_description; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_description IS 'Provider Description / شرح ارائه‌دهنده';


--
-- Name: COLUMN t_ai_provider.c_state; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_state IS 'Provider State / وضعیت ارائه‌دهنده';


--
-- Name: COLUMN t_ai_provider.c_created_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_created_at IS 'Creation Time / زمان ایجاد';


--
-- Name: COLUMN t_ai_provider.c_updated_at; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_ai_provider.c_updated_at IS 'Last Update Time / زمان آخرین تغییر';


--
-- Name: t_avatar_manager; Type: TABLE; Schema: pulsar; Owner: -
--

CREATE TABLE pulsar.t_avatar_manager (
    c_avatar_manager_id bigint NOT NULL,
    c_avatar_manager_desc text NOT NULL
);


--
-- Name: TABLE t_avatar_manager; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON TABLE pulsar.t_avatar_manager IS 'Avatar manager @ROOT@';


--
-- Name: COLUMN t_avatar_manager.c_avatar_manager_id; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_avatar_manager.c_avatar_manager_id IS 'Avatar Manager ID / شناسه مدیر آواتار';


--
-- Name: COLUMN t_avatar_manager.c_avatar_manager_desc; Type: COMMENT; Schema: pulsar; Owner: -
--

COMMENT ON COLUMN pulsar.t_avatar_manager.c_avatar_manager_desc IS 'Avatar Manager Description / شرح مدیر آواتار';


--
-- Name: t_avatar_manager_c_avatar_manager_id_seq; Type: SEQUENCE; Schema: pulsar; Owner: -
--

CREATE SEQUENCE pulsar.t_avatar_manager_c_avatar_manager_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: t_avatar_manager_c_avatar_manager_id_seq; Type: SEQUENCE OWNED BY; Schema: pulsar; Owner: -
--

ALTER SEQUENCE pulsar.t_avatar_manager_c_avatar_manager_id_seq OWNED BY pulsar.t_avatar_manager.c_avatar_manager_id;


--
-- Name: t_avatar_manager c_avatar_manager_id; Type: DEFAULT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_avatar_manager ALTER COLUMN c_avatar_manager_id SET DEFAULT nextval('pulsar.t_avatar_manager_c_avatar_manager_id_seq'::regclass);


--
-- Name: t_ai_context pk_t_ai_context; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_context
    ADD CONSTRAINT pk_t_ai_context PRIMARY KEY (c_ai_context_id);


--
-- Name: t_ai_definition pk_t_ai_definition; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition
    ADD CONSTRAINT pk_t_ai_definition PRIMARY KEY (c_ai_definition_id);


--
-- Name: t_ai_definition_context pk_t_ai_definition_context; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_context
    ADD CONSTRAINT pk_t_ai_definition_context PRIMARY KEY (c_ai_definition_context_id);


--
-- Name: t_ai_definition_model pk_t_ai_definition_model; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_model
    ADD CONSTRAINT pk_t_ai_definition_model PRIMARY KEY (c_ai_definition_model_id);


--
-- Name: t_ai_definition_operation pk_t_ai_definition_operation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_operation
    ADD CONSTRAINT pk_t_ai_definition_operation PRIMARY KEY (c_ai_definition_operation_id);


--
-- Name: t_ai_definition_policy pk_t_ai_definition_policy; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_policy
    ADD CONSTRAINT pk_t_ai_definition_policy PRIMARY KEY (c_ai_definition_policy_id);


--
-- Name: t_ai_definition_presentation pk_t_ai_definition_presentation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_presentation
    ADD CONSTRAINT pk_t_ai_definition_presentation PRIMARY KEY (c_ai_definition_presentation_id);


--
-- Name: t_ai_model pk_t_ai_model; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_model
    ADD CONSTRAINT pk_t_ai_model PRIMARY KEY (c_ai_model_id);


--
-- Name: t_ai_operation pk_t_ai_operation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_operation
    ADD CONSTRAINT pk_t_ai_operation PRIMARY KEY (c_ai_operation_id);


--
-- Name: t_ai_policy pk_t_ai_policy; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_policy
    ADD CONSTRAINT pk_t_ai_policy PRIMARY KEY (c_ai_policy_id);


--
-- Name: t_ai_presentation pk_t_ai_presentation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_presentation
    ADD CONSTRAINT pk_t_ai_presentation PRIMARY KEY (c_ai_presentation_id);


--
-- Name: t_ai_provider pk_t_ai_provider; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_provider
    ADD CONSTRAINT pk_t_ai_provider PRIMARY KEY (c_ai_provider_id);


--
-- Name: t_ai_avatar_assignment t_ai_avatar_assignment_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_assignment
    ADD CONSTRAINT t_ai_avatar_assignment_pkey PRIMARY KEY (c_assignment_id);


--
-- Name: t_ai_avatar_conversation t_ai_avatar_conversation_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_conversation
    ADD CONSTRAINT t_ai_avatar_conversation_pkey PRIMARY KEY (c_conversation_id);


--
-- Name: t_ai_avatar_memory t_ai_avatar_memory_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory
    ADD CONSTRAINT t_ai_avatar_memory_pkey PRIMARY KEY (c_memory_id);


--
-- Name: t_ai_avatar_memory_policy t_ai_avatar_memory_policy_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory_policy
    ADD CONSTRAINT t_ai_avatar_memory_policy_pkey PRIMARY KEY (c_policy_id);


--
-- Name: t_ai_avatar_message t_ai_avatar_message_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_message
    ADD CONSTRAINT t_ai_avatar_message_pkey PRIMARY KEY (c_message_id);


--
-- Name: t_avatar_manager t_avatar_manager_pkey; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_avatar_manager
    ADD CONSTRAINT t_avatar_manager_pkey PRIMARY KEY (c_avatar_manager_id);


--
-- Name: t_ai_avatar_assignment uq_ai_avatar_assignment_identity; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_assignment
    ADD CONSTRAINT uq_ai_avatar_assignment_identity UNIQUE (c_assignment_id, c_user_id, c_ai_definition_id);


--
-- Name: t_ai_avatar_assignment uq_ai_avatar_assignment_user_definition; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_assignment
    ADD CONSTRAINT uq_ai_avatar_assignment_user_definition UNIQUE (c_user_id, c_ai_definition_id);


--
-- Name: t_ai_avatar_conversation uq_ai_avatar_conversation_identity; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_conversation
    ADD CONSTRAINT uq_ai_avatar_conversation_identity UNIQUE (c_conversation_id, c_user_id, c_ai_definition_id);


--
-- Name: t_ai_avatar_memory_policy uq_ai_avatar_memory_policy_definition; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory_policy
    ADD CONSTRAINT uq_ai_avatar_memory_policy_definition UNIQUE (c_ai_definition_id);


--
-- Name: t_ai_avatar_message uq_ai_avatar_message_identity; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_message
    ADD CONSTRAINT uq_ai_avatar_message_identity UNIQUE (c_message_id, c_user_id, c_ai_definition_id);


--
-- Name: t_ai_context uq_t_ai_context_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_context
    ADD CONSTRAINT uq_t_ai_context_code UNIQUE (c_context_code);


--
-- Name: t_ai_definition uq_t_ai_definition_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition
    ADD CONSTRAINT uq_t_ai_definition_code UNIQUE (c_definition_code);


--
-- Name: t_ai_definition_context uq_t_ai_definition_context; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_context
    ADD CONSTRAINT uq_t_ai_definition_context UNIQUE (c_ai_definition_id, c_ai_context_id);


--
-- Name: t_ai_definition_model uq_t_ai_definition_model; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_model
    ADD CONSTRAINT uq_t_ai_definition_model UNIQUE (c_ai_definition_id, c_ai_model_id);


--
-- Name: t_ai_definition_operation uq_t_ai_definition_operation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_operation
    ADD CONSTRAINT uq_t_ai_definition_operation UNIQUE (c_ai_definition_id, c_ai_operation_id);


--
-- Name: t_ai_definition_policy uq_t_ai_definition_policy; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_policy
    ADD CONSTRAINT uq_t_ai_definition_policy UNIQUE (c_ai_definition_id, c_ai_policy_id);


--
-- Name: t_ai_definition_presentation uq_t_ai_definition_presentation; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_presentation
    ADD CONSTRAINT uq_t_ai_definition_presentation UNIQUE (c_ai_definition_id, c_ai_presentation_id);


--
-- Name: t_ai_model uq_t_ai_model_provider_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_model
    ADD CONSTRAINT uq_t_ai_model_provider_code UNIQUE (c_ai_provider_id, c_model_code);


--
-- Name: t_ai_operation uq_t_ai_operation_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_operation
    ADD CONSTRAINT uq_t_ai_operation_code UNIQUE (c_operation_code);


--
-- Name: t_ai_policy uq_t_ai_policy_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_policy
    ADD CONSTRAINT uq_t_ai_policy_code UNIQUE (c_policy_code);


--
-- Name: t_ai_presentation uq_t_ai_presentation_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_presentation
    ADD CONSTRAINT uq_t_ai_presentation_code UNIQUE (c_presentation_code);


--
-- Name: t_ai_provider uq_t_ai_provider_code; Type: CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_provider
    ADD CONSTRAINT uq_t_ai_provider_code UNIQUE (c_provider_code);


--
-- Name: ix_ai_avatar_assignment_user_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_assignment_user_state ON pulsar.t_ai_avatar_assignment USING btree (c_user_id, c_state);


--
-- Name: ix_ai_avatar_conversation_expiry; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_conversation_expiry ON pulsar.t_ai_avatar_conversation USING btree (c_expires_at);


--
-- Name: ix_ai_avatar_conversation_owner; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_conversation_owner ON pulsar.t_ai_avatar_conversation USING btree (c_user_id, c_ai_definition_id, c_last_message_at DESC);


--
-- Name: ix_ai_avatar_memory_owner_expiry; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_memory_owner_expiry ON pulsar.t_ai_avatar_memory USING btree (c_user_id, c_ai_definition_id, c_expires_at);


--
-- Name: ix_ai_avatar_memory_policy_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_memory_policy_state ON pulsar.t_ai_avatar_memory_policy USING btree (c_state);


--
-- Name: ix_ai_avatar_memory_source; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_memory_source ON pulsar.t_ai_avatar_memory USING btree (c_source_message_id);


--
-- Name: ix_ai_avatar_message_history; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_message_history ON pulsar.t_ai_avatar_message USING btree (c_conversation_id, c_created_at, c_message_id);


--
-- Name: ix_ai_avatar_message_owner; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_ai_avatar_message_owner ON pulsar.t_ai_avatar_message USING btree (c_user_id, c_ai_definition_id, c_created_at);


--
-- Name: ix_t_ai_context_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_context_state ON pulsar.t_ai_context USING btree (c_state);


--
-- Name: ix_t_ai_context_type; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_context_type ON pulsar.t_ai_context USING btree (c_context_type);


--
-- Name: ix_t_ai_definition_context_context; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_context_context ON pulsar.t_ai_definition_context USING btree (c_ai_context_id);


--
-- Name: ix_t_ai_definition_context_definition; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_context_definition ON pulsar.t_ai_definition_context USING btree (c_ai_definition_id);


--
-- Name: ix_t_ai_definition_context_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_context_state ON pulsar.t_ai_definition_context USING btree (c_state);


--
-- Name: ix_t_ai_definition_model_definition; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_model_definition ON pulsar.t_ai_definition_model USING btree (c_ai_definition_id);


--
-- Name: ix_t_ai_definition_model_model; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_model_model ON pulsar.t_ai_definition_model USING btree (c_ai_model_id);


--
-- Name: ix_t_ai_definition_model_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_model_state ON pulsar.t_ai_definition_model USING btree (c_state);


--
-- Name: ix_t_ai_definition_operation_definition; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_operation_definition ON pulsar.t_ai_definition_operation USING btree (c_ai_definition_id);


--
-- Name: ix_t_ai_definition_operation_operation; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_operation_operation ON pulsar.t_ai_definition_operation USING btree (c_ai_operation_id);


--
-- Name: ix_t_ai_definition_operation_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_operation_state ON pulsar.t_ai_definition_operation USING btree (c_state);


--
-- Name: ix_t_ai_definition_policy_definition; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_policy_definition ON pulsar.t_ai_definition_policy USING btree (c_ai_definition_id);


--
-- Name: ix_t_ai_definition_policy_policy; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_policy_policy ON pulsar.t_ai_definition_policy USING btree (c_ai_policy_id);


--
-- Name: ix_t_ai_definition_policy_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_policy_state ON pulsar.t_ai_definition_policy USING btree (c_state);


--
-- Name: ix_t_ai_definition_presentation_definition; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_presentation_definition ON pulsar.t_ai_definition_presentation USING btree (c_ai_definition_id);


--
-- Name: ix_t_ai_definition_presentation_presentation; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_presentation_presentation ON pulsar.t_ai_definition_presentation USING btree (c_ai_presentation_id);


--
-- Name: ix_t_ai_definition_presentation_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_presentation_state ON pulsar.t_ai_definition_presentation USING btree (c_state);


--
-- Name: ix_t_ai_definition_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_definition_state ON pulsar.t_ai_definition USING btree (c_state);


--
-- Name: ix_t_ai_model_provider; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_model_provider ON pulsar.t_ai_model USING btree (c_ai_provider_id);


--
-- Name: ix_t_ai_model_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_model_state ON pulsar.t_ai_model USING btree (c_state);


--
-- Name: ix_t_ai_operation_model; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_operation_model ON pulsar.t_ai_operation USING btree (c_ai_model_id);


--
-- Name: ix_t_ai_operation_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_operation_state ON pulsar.t_ai_operation USING btree (c_state);


--
-- Name: ix_t_ai_policy_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_policy_state ON pulsar.t_ai_policy USING btree (c_state);


--
-- Name: ix_t_ai_policy_type; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_policy_type ON pulsar.t_ai_policy USING btree (c_policy_type);


--
-- Name: ix_t_ai_presentation_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_presentation_state ON pulsar.t_ai_presentation USING btree (c_state);


--
-- Name: ix_t_ai_presentation_type; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_presentation_type ON pulsar.t_ai_presentation USING btree (c_presentation_type);


--
-- Name: ix_t_ai_provider_state; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE INDEX ix_t_ai_provider_state ON pulsar.t_ai_provider USING btree (c_state);


--
-- Name: ux_t_avatar_manager_desc; Type: INDEX; Schema: pulsar; Owner: -
--

CREATE UNIQUE INDEX ux_t_avatar_manager_desc ON pulsar.t_avatar_manager USING btree (c_avatar_manager_desc);


--
-- Name: t_ai_context trg_t_ai_context_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_context_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_context FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_context_log();


--
-- Name: t_ai_definition_context trg_t_ai_definition_context_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_context_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition_context FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_context_log();


--
-- Name: t_ai_definition trg_t_ai_definition_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_log();


--
-- Name: t_ai_definition_model trg_t_ai_definition_model_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_model_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition_model FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_model_log();


--
-- Name: t_ai_definition_operation trg_t_ai_definition_operation_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_operation_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition_operation FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_operation_log();


--
-- Name: t_ai_definition_policy trg_t_ai_definition_policy_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_policy_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition_policy FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_policy_log();


--
-- Name: t_ai_definition_presentation trg_t_ai_definition_presentation_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_definition_presentation_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_definition_presentation FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_definition_presentation_log();


--
-- Name: t_ai_model trg_t_ai_model_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_model_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_model FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_model_log();


--
-- Name: t_ai_operation trg_t_ai_operation_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_operation_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_operation FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_operation_log();


--
-- Name: t_ai_policy trg_t_ai_policy_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_policy_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_policy FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_policy_log();


--
-- Name: t_ai_presentation trg_t_ai_presentation_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_presentation_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_presentation FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_presentation_log();


--
-- Name: t_ai_provider trg_t_ai_provider_log; Type: TRIGGER; Schema: pulsar; Owner: -
--

CREATE TRIGGER trg_t_ai_provider_log AFTER INSERT OR DELETE OR UPDATE ON pulsar.t_ai_provider FOR EACH ROW EXECUTE FUNCTION pulsar.fn_t_ai_provider_log();


--
-- Name: t_ai_avatar_assignment fk_ai_avatar_assignment_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_assignment
    ADD CONSTRAINT fk_ai_avatar_assignment_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE RESTRICT;


--
-- Name: t_ai_avatar_assignment fk_ai_avatar_assignment_user; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_assignment
    ADD CONSTRAINT fk_ai_avatar_assignment_user FOREIGN KEY (c_user_id) REFERENCES pulsar.t_user(c_user_id) ON DELETE CASCADE;


--
-- Name: t_ai_avatar_conversation fk_ai_avatar_conversation_assignment; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_conversation
    ADD CONSTRAINT fk_ai_avatar_conversation_assignment FOREIGN KEY (c_user_id, c_ai_definition_id) REFERENCES pulsar.t_ai_avatar_assignment(c_user_id, c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_avatar_memory fk_ai_avatar_memory_assignment; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory
    ADD CONSTRAINT fk_ai_avatar_memory_assignment FOREIGN KEY (c_user_id, c_ai_definition_id) REFERENCES pulsar.t_ai_avatar_assignment(c_user_id, c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_avatar_memory_policy fk_ai_avatar_memory_policy_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory_policy
    ADD CONSTRAINT fk_ai_avatar_memory_policy_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_avatar_memory_policy fk_ai_avatar_memory_policy_updated_by; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory_policy
    ADD CONSTRAINT fk_ai_avatar_memory_policy_updated_by FOREIGN KEY (c_updated_by) REFERENCES pulsar.t_user(c_user_id) ON DELETE SET NULL;


--
-- Name: t_ai_avatar_memory fk_ai_avatar_memory_source; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_memory
    ADD CONSTRAINT fk_ai_avatar_memory_source FOREIGN KEY (c_source_message_id, c_user_id, c_ai_definition_id) REFERENCES pulsar.t_ai_avatar_message(c_message_id, c_user_id, c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_avatar_message fk_ai_avatar_message_conversation; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_avatar_message
    ADD CONSTRAINT fk_ai_avatar_message_conversation FOREIGN KEY (c_conversation_id, c_user_id, c_ai_definition_id) REFERENCES pulsar.t_ai_avatar_conversation(c_conversation_id, c_user_id, c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_context fk_t_ai_context_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_context
    ADD CONSTRAINT fk_t_ai_context_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition fk_t_ai_definition_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition
    ADD CONSTRAINT fk_t_ai_definition_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition_context fk_t_ai_definition_context_context; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_context
    ADD CONSTRAINT fk_t_ai_definition_context_context FOREIGN KEY (c_ai_context_id) REFERENCES pulsar.t_ai_context(c_ai_context_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition_context fk_t_ai_definition_context_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_context
    ADD CONSTRAINT fk_t_ai_definition_context_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_definition_model fk_t_ai_definition_model_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_model
    ADD CONSTRAINT fk_t_ai_definition_model_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_definition_model fk_t_ai_definition_model_model; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_model
    ADD CONSTRAINT fk_t_ai_definition_model_model FOREIGN KEY (c_ai_model_id) REFERENCES pulsar.t_ai_model(c_ai_model_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition_operation fk_t_ai_definition_operation_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_operation
    ADD CONSTRAINT fk_t_ai_definition_operation_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_definition_operation fk_t_ai_definition_operation_operation; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_operation
    ADD CONSTRAINT fk_t_ai_definition_operation_operation FOREIGN KEY (c_ai_operation_id) REFERENCES pulsar.t_ai_operation(c_ai_operation_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition_policy fk_t_ai_definition_policy_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_policy
    ADD CONSTRAINT fk_t_ai_definition_policy_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_definition_policy fk_t_ai_definition_policy_policy; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_policy
    ADD CONSTRAINT fk_t_ai_definition_policy_policy FOREIGN KEY (c_ai_policy_id) REFERENCES pulsar.t_ai_policy(c_ai_policy_id) ON DELETE RESTRICT;


--
-- Name: t_ai_definition_presentation fk_t_ai_definition_presentation_definition; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_presentation
    ADD CONSTRAINT fk_t_ai_definition_presentation_definition FOREIGN KEY (c_ai_definition_id) REFERENCES pulsar.t_ai_definition(c_ai_definition_id) ON DELETE CASCADE;


--
-- Name: t_ai_definition_presentation fk_t_ai_definition_presentation_presentation; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_definition_presentation
    ADD CONSTRAINT fk_t_ai_definition_presentation_presentation FOREIGN KEY (c_ai_presentation_id) REFERENCES pulsar.t_ai_presentation(c_ai_presentation_id) ON DELETE RESTRICT;


--
-- Name: t_ai_model fk_t_ai_model_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_model
    ADD CONSTRAINT fk_t_ai_model_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_operation fk_t_ai_operation_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_operation
    ADD CONSTRAINT fk_t_ai_operation_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_policy fk_t_ai_policy_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_policy
    ADD CONSTRAINT fk_t_ai_policy_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_presentation fk_t_ai_presentation_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_presentation
    ADD CONSTRAINT fk_t_ai_presentation_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- Name: t_ai_provider fk_t_ai_provider_avatar_manager; Type: FK CONSTRAINT; Schema: pulsar; Owner: -
--

ALTER TABLE ONLY pulsar.t_ai_provider
    ADD CONSTRAINT fk_t_ai_provider_avatar_manager FOREIGN KEY (c_avatar_manager_id) REFERENCES pulsar.t_avatar_manager(c_avatar_manager_id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

