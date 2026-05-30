#!/bin/bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
[auth]
redirect_uri  = "$AUTH_REDIRECT_URI"
cookie_secret = "$COOKIE_SECRET"

[auth.google]
client_id           = "$GOOGLE_CLIENT_ID"
client_secret       = "$GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[supabase]
url              = "$SUPABASE_URL"
service_role_key = "$SUPABASE_SERVICE_ROLE_KEY"
EOF

streamlit run research_app.py --server.port $PORT --server.headless true --server.address 0.0.0.0
