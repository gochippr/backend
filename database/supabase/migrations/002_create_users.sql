-- Create users table with IDP information
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idp_id VARCHAR(255) NOT NULL UNIQUE, -- External ID from identity provider (Google, etc.)
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) UNIQUE,
    given_name VARCHAR(100),
    family_name VARCHAR(100),
    full_name VARCHAR(255),
    photo_url TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    provider VARCHAR(50) NOT NULL, -- 'google', 'apple', etc.
    locale VARCHAR(10), -- 'en-US', 'es-ES', etc.
    timezone VARCHAR(50), -- 'America/New_York', etc.
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS friendships (
  user_id        UUID NOT NULL,
  friend_user_id UUID NOT NULL,
  status         VARCHAR NOT NULL DEFAULT 'pending',
  created_at     TIMESTAMP DEFAULT now(),
  updated_at     TIMESTAMP DEFAULT now(),
  deleted_at     TIMESTAMP DEFAULT NULL,
  CONSTRAINT friendships_pkey PRIMARY KEY (user_id, friend_user_id)
);

