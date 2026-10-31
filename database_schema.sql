-- PostgreSQL reference schema derived from the current Django ORM models.
-- Django migrations remain the authoritative mechanism for creating databases.

CREATE TABLE organization (
    id UUID PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(60) UNIQUE NOT NULL,
    plan VARCHAR(16) NOT NULL DEFAULT 'starter',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE "user" (
    id UUID PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP NOT NULL
);

CREATE TABLE membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(user_id, organization_id)
);

CREATE TABLE email_token (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    purpose VARCHAR(16) NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE uml_document (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    owner_id VARCHAR(255) NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE deployment (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES uml_document(id) ON DELETE CASCADE,
    created_by UUID REFERENCES "user"(id) ON DELETE SET NULL,
    status VARCHAR(16) NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    log_tail TEXT NOT NULL DEFAULT '',
    public_path VARCHAR(128) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX users_user_email_ci_unique ON "user"(LOWER(email));
CREATE INDEX idx_membership_organization_role ON membership(organization_id, role);
CREATE INDEX idx_email_token_user_purpose_created ON email_token(user_id, purpose, created_at);
CREATE INDEX idx_umldoc_organization_owner ON uml_document(organization_id, owner_id);
CREATE INDEX idx_deployment_organization_status ON deployment(organization_id, status);
