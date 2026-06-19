import streamlit as st
from auth.supabase_auth import sign_in, AUTH_CSS

def render_signin_page():
    # Inject CSS
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # Background blobs
    st.markdown("""
    <div class="auth-bg">
        <div class="auth-blob blob-1"></div>
        <div class="auth-blob blob-2"></div>
        <div class="auth-blob blob-3"></div>
    </div>
    """, unsafe_allow_html=True)

    # Logo
    st.markdown("""
    <div class="auth-logo">
        <div class="auth-logo-mark">C</div>
        <div class="auth-logo-name">Calipr</div>
        <div class="auth-logo-tagline">AI Candidate Ranking Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # Card open
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)

    # Heading
    st.markdown("""
    <div class="auth-heading">Welcome back</div>
    <div class="auth-subheading">Sign in to your Calipr account to continue ranking.</div>
    """, unsafe_allow_html=True)

    # Google OAuth button (static UI)
    st.markdown("""
    <button class="google-btn" onclick="void(0)">
        <svg width="18" height="18" viewBox="0 0 18 18">
            <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/>
            <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/>
            <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"/>
            <path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.3z"/>
        </svg>
        Continue with Google
    </button>
    """, unsafe_allow_html=True)

    # OR divider
    st.markdown("""
    <div class="or-divider"><span>or</span></div>
    """, unsafe_allow_html=True)

    # Form fields
    email    = st.text_input("Email address", placeholder="you@company.com",
                              key="signin_email")
    password = st.text_input("Password", placeholder="Enter your password",
                              type="password", key="signin_password")

    # Forgot password link
    st.markdown("""
    <div class="forgot-row">
        <span class="auth-link" id="forgot-link">Forgot password?</span>
    </div>
    """, unsafe_allow_html=True)

    # Sign In button
    if st.button("Sign In", key="signin_btn", use_container_width=True):
        if not email or not password:
            st.error("Please enter your email and password.")
        else:
            with st.spinner("Signing in..."):
                try:
                    response = sign_in(email, password)
                    user = response.user
                    session = response.session
                    if user:
                        st.session_state.user         = user
                        st.session_state.access_token = session.access_token
                        st.session_state.user_email   = user.email
                        st.session_state.user_name    = user.user_metadata.get("full_name", email.split("@")[0])
                        st.success("✓ Signed in successfully!")
                        st.rerun()
                    else:
                        st.error("Sign in failed. Please check your credentials.")
                except Exception as e:
                    err = str(e).lower()
                    if "invalid" in err or "credentials" in err:
                        st.error("Incorrect email or password. Please try again.")
                    elif "email" in err and "confirm" in err:
                        st.error("Please verify your email before signing in.")
                    else:
                        st.error(f"Sign in failed: {e}")

    # Card close
    st.markdown('</div>', unsafe_allow_html=True)

    # Switch to Sign Up
    st.markdown("""
    <div class="switch-row">
        Don't have an account?
        <span class="auth-link" style="margin-left:4px;">Create one</span>
    </div>
    """, unsafe_allow_html=True)

    # Terms
    st.markdown("""
    <div class="terms-text">
        By signing in, you agree to our
        <a>Terms of Service</a> and <a>Privacy Policy</a>.
    </div>
    """, unsafe_allow_html=True)

    # Handle toggle via session state
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Create an account →", key="goto_signup"):
            st.session_state.auth_page = "signup"
            st.rerun()
