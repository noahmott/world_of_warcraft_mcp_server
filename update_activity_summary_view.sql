-- Update user_activity_summary view to include oauth_user_id
CREATE OR REPLACE VIEW public.user_activity_summary AS
SELECT
    u.id as user_id,
    u.oauth_provider,
    u.oauth_user_id,
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
GROUP BY u.id, u.oauth_provider, u.oauth_user_id, u.email, u.username, u.display_name,
         u.first_seen_at, u.last_seen_at, u.total_tool_calls, u.total_sessions;
