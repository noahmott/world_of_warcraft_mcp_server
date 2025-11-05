-- Migration: Create user tracking tables for OAuth authenticated users
-- Description: Track authenticated users and their tool usage patterns

-- Create users table to store authenticated user information
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- OAuth Provider Information
    oauth_provider VARCHAR(50) NOT NULL, -- 'discord' or 'google'
    oauth_user_id VARCHAR(255) NOT NULL, -- User ID from OAuth provider

    -- User Profile Information
    email VARCHAR(255),
    username VARCHAR(255),
    display_name VARCHAR(255),
    avatar_url TEXT,

    -- Timestamps
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Usage Statistics
    total_tool_calls INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Constraints
    UNIQUE(oauth_provider, oauth_user_id),
    CONSTRAINT valid_provider CHECK (oauth_provider IN ('discord', 'google'))
);

-- Create index for fast lookup by OAuth credentials
CREATE INDEX IF NOT EXISTS idx_users_oauth ON public.users(oauth_provider, oauth_user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON public.users(last_seen_at DESC);

-- Create user_sessions table to track active sessions
CREATE TABLE IF NOT EXISTS public.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

    -- Session Information
    session_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_end TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,

    -- Connection Details
    client_type VARCHAR(100), -- 'claude_desktop', 'mcp_inspector', etc.
    client_version VARCHAR(50),
    ip_address INET,
    user_agent TEXT,

    -- Session Statistics
    tool_calls_count INTEGER DEFAULT 0,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for session queries
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON public.user_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON public.user_sessions(last_activity_at DESC);

-- Modify activity_logs table to add user tracking columns
ALTER TABLE public.activity_logs
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS session_id_ref UUID REFERENCES public.user_sessions(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS oauth_user_id VARCHAR(255);

-- Create indexes on activity_logs for user queries
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON public.activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_session_id_ref ON public.activity_logs(session_id_ref);
CREATE INDEX IF NOT EXISTS idx_activity_logs_oauth ON public.activity_logs(oauth_provider, oauth_user_id);

-- Create a view for user activity summary
CREATE OR REPLACE VIEW public.user_activity_summary AS
SELECT
    u.id as user_id,
    u.oauth_provider,
    u.email,
    u.username,
    u.display_name,
    u.first_seen_at,
    u.last_seen_at,
    u.total_tool_calls,
    u.total_sessions,
    COUNT(DISTINCT us.id) as active_sessions_count,
    COUNT(al.id) as activity_logs_count,
    MAX(al.timestamp) as last_tool_call_at
FROM public.users u
LEFT JOIN public.user_sessions us ON u.id = us.user_id AND us.is_active = TRUE
LEFT JOIN public.activity_logs al ON u.id = al.user_id
GROUP BY u.id, u.oauth_provider, u.email, u.username, u.display_name,
         u.first_seen_at, u.last_seen_at, u.total_tool_calls, u.total_sessions;

-- Create function to update user last_seen_at timestamp
CREATE OR REPLACE FUNCTION update_user_last_seen()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.users
    SET last_seen_at = NOW(),
        total_tool_calls = total_tool_calls + 1
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update user last_seen_at on activity
CREATE TRIGGER trigger_update_user_last_seen
AFTER INSERT ON public.activity_logs
FOR EACH ROW
WHEN (NEW.user_id IS NOT NULL)
EXECUTE FUNCTION update_user_last_seen();

-- Create function to update session statistics
CREATE OR REPLACE FUNCTION update_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.user_sessions
    SET tool_calls_count = tool_calls_count + 1,
        last_activity_at = NOW()
    WHERE id = NEW.session_id_ref;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update session stats on activity
CREATE TRIGGER trigger_update_session_stats
AFTER INSERT ON public.activity_logs
FOR EACH ROW
WHEN (NEW.session_id_ref IS NOT NULL)
EXECUTE FUNCTION update_session_stats();

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policies for service role (your MCP server)
CREATE POLICY "Service role can do everything on users"
ON public.users FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Service role can do everything on user_sessions"
ON public.user_sessions FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Create policies for anon role (read-only access for debugging)
CREATE POLICY "Anon can read users"
ON public.users FOR SELECT
TO anon
USING (true);

CREATE POLICY "Anon can read user_sessions"
ON public.user_sessions FOR SELECT
TO anon
USING (true);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE ON public.users TO service_role;
GRANT SELECT, INSERT, UPDATE ON public.user_sessions TO service_role;
GRANT SELECT ON public.user_activity_summary TO service_role;
GRANT SELECT ON public.users TO anon;
GRANT SELECT ON public.user_sessions TO anon;
GRANT SELECT ON public.user_activity_summary TO anon;

-- Add comments for documentation
COMMENT ON TABLE public.users IS 'Stores authenticated user information from OAuth providers (Discord/Google)';
COMMENT ON TABLE public.user_sessions IS 'Tracks user sessions with MCP clients (Claude Desktop, MCP Inspector, etc)';
COMMENT ON COLUMN public.users.oauth_provider IS 'OAuth provider used for authentication (discord or google)';
COMMENT ON COLUMN public.users.oauth_user_id IS 'Unique user ID from the OAuth provider';
COMMENT ON COLUMN public.users.total_tool_calls IS 'Lifetime count of tool calls made by this user';
COMMENT ON COLUMN public.user_sessions.is_active IS 'Whether this session is currently active';
COMMENT ON VIEW public.user_activity_summary IS 'Summary view of user activity including tool usage statistics';
