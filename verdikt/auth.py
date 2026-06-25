# auth.py
# Calipr — Authentication & Plan Management
# Supabase email+password auth with plan stored in user_metadata

import streamlit as st
from supabase_client import get_supabase

# ─────────────────────────────────────────
# SESSION STATE HELPERS
# ─────────────────────────────────────────

def init_session():
    """Initialize all auth-related session state keys."""
    defaults = {
        "authenticated":  False,
        "user":           None,      # Supabase user object
        "user_email":     "",
        "user_name":      "",
        "user_plan":      "free",    # free | pro | enterprise
        "user_initials":  "?",
        "auth_page":      "signin",  # signin | signup
        "auth_error":     "",
        "auth_success":   "",
        "selected_plan":  "pro",     # pre-selected on signup page
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_plan() -> str:
    """Return the current user's plan. Safe to call anywhere."""
    return st.session_state.get("user_plan", "free")


def is_pro() -> bool:
    return get_plan() in ("pro", "enterprise")


def is_enterprise() -> bool:
    return get_plan() == "enterprise"


def sign_out():
    """Clear all session state and sign out from Supabase."""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
    except Exception:
        pass
    keys_to_clear = [
        "authenticated", "user", "user_email", "user_name",
        "user_plan", "user_initials", "auth_error", "auth_success",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


def _extract_user_info(user):
    """Pull name, plan, initials from Supabase user object."""
    metadata = user.user_metadata or {}
    name     = metadata.get("full_name", user.email.split("@")[0].title())
    plan     = metadata.get("plan", "free")
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
    return name, plan, initials


# ─────────────────────────────────────────
# SIGN IN
# ─────────────────────────────────────────

def sign_in(email: str, password: str) -> bool:
    """
    Authenticate with Supabase. Returns True on success.
    Sets session state on success, sets auth_error on failure.
    """
    st.session_state.auth_error = ""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email":    email.strip().lower(),
            "password": password,
        })
        user = response.user
        if user:
            name, plan, initials = _extract_user_info(user)
            st.session_state.authenticated = True
            st.session_state.user          = user
            st.session_state.user_email    = user.email
            st.session_state.user_name     = name
            st.session_state.user_plan     = plan
            st.session_state.user_initials = initials
            return True
        else:
            st.session_state.auth_error = "Invalid email or password."
            return False
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "credentials" in err:
            st.session_state.auth_error = "Invalid email or password."
        elif "email" in err and "confirm" in err:
            st.session_state.auth_error = "Please confirm your email before signing in."
        elif "not found" in err:
            st.session_state.auth_error = "No account found with this email."
        else:
            st.session_state.auth_error = "Sign in failed. Please try again."
        return False


# ─────────────────────────────────────────
# SIGN UP
# ─────────────────────────────────────────

def sign_up(full_name: str, email: str, password: str, plan: str = "free") -> bool:
    """
    Create a new Supabase account with plan stored in user_metadata.
    Returns True on success.
    """
    st.session_state.auth_error   = ""
    st.session_state.auth_success = ""
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email":    email.strip().lower(),
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name.strip(),
                    "plan":      plan,
                }
            }
        })
        user = response.user
        if user:
            # Auto sign in after signup (email confirmation disabled in Supabase dashboard)
            return sign_in(email, password)
        else:
            st.session_state.auth_error = "Sign up failed. Please try again."
            return False
    except Exception as e:
        err = str(e).lower()
        if "already registered" in err or "already exists" in err:
            st.session_state.auth_error = "An account with this email already exists. Sign in instead."
        elif "password" in err and ("short" in err or "weak" in err or "length" in err):
            st.session_state.auth_error = "Password must be at least 8 characters."
        elif "invalid email" in err:
            st.session_state.auth_error = "Please enter a valid email address."
        else:
            st.session_state.auth_error = "Sign up failed. Please try again."
        return False


# ─────────────────────────────────────────
# SIGN IN PAGE UI
# ─────────────────────────────────────────

def render_sign_in():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
      html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background: #FFFFFF !important;
      }
      #MainMenu, footer, header { visibility: hidden; }
      .block-container {
        padding: 0 !important;
        max-width: 100% !important;
      }
      /* Input styling */
      [data-testid="stTextInput"] input {
        height: 44px !important;
        border: 1.5px solid #E5E7EB !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        padding: 0 14px !important;
        transition: border-color 0.15s ease !important;
        font-family: 'Inter', sans-serif !important;
      }
      [data-testid="stTextInput"] input:focus {
        border-color: #4A90FF !important;
        box-shadow: 0 0 0 3px rgba(74,144,255,0.12) !important;
      }
      /* Button styling */
      [data-testid="stButton"] button {
        height: 44px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.15s ease !important;
      }
      /* Hide label for inputs */
      [data-testid="stTextInput"] label { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Center the auth card
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("""
        <div style="min-height:100vh; display:flex; flex-direction:column;
                    justify-content:center; padding: 60px 0;">

          <!-- Logo -->
          <div style="text-align:center; margin-bottom:40px;">
            <div style="display:inline-flex; align-items:center; gap:10px;">
              <div style="width:36px; height:36px; background:#0A0A0A;
                          border-radius:8px; display:flex; align-items:center;
                          justify-content:center;">
                <span style="color:white; font-weight:800;
                             font-size:18px; font-family:Inter,sans-serif;">C</span>
              </div>
              <span style="font-size:22px; font-weight:800;
                           letter-spacing:-0.04em; color:#0A0A0A;">Calipr</span>
              <span style="background:#0A0A0A; color:white; font-size:10px;
                           font-weight:700; padding:2px 7px; border-radius:4px;
                           letter-spacing:0.05em;">PRO</span>
            </div>
          </div>

          <!-- Card -->
          <div style="background:#FFFFFF; border:1px solid #F3F4F6;
                      border-radius:16px; padding:36px 32px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.06);">

            <h2 style="font-size:22px; font-weight:800; letter-spacing:-0.03em;
                       color:#0A0A0A; margin:0 0 6px 0; text-align:center;">
              Welcome back
            </h2>
            <p style="font-size:14px; color:#6B7280; text-align:center;
                      margin:0 0 28px 0;">
              Sign in to your Calipr account
            </p>
        """, unsafe_allow_html=True)

        # Google OAuth button (UI only)
        st.markdown("""
            <button onclick="return false;" style="
              width:100%; height:44px; background:#FFFFFF;
              border:1.5px solid #E5E7EB; border-radius:8px;
              display:flex; align-items:center; justify-content:center;
              gap:10px; cursor:pointer; font-size:14px; font-weight:500;
              color:#374151; font-family:Inter,sans-serif;
              margin-bottom:20px; transition:border-color 0.15s ease;">
              <svg width="18" height="18" viewBox="0 0 18 18">
                <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
                <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
                <path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"/>
                <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z"/>
              </svg>
              Continue with Google
            </button>
        """, unsafe_allow_html=True)

        # OR divider
        st.markdown("""
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
              <div style="flex:1; height:1px; background:#F3F4F6;"></div>
              <span style="font-size:12px; color:#9CA3AF; font-weight:500;">OR</span>
              <div style="flex:1; height:1px; background:#F3F4F6;"></div>
            </div>
        """, unsafe_allow_html=True)

        # Error message
        if st.session_state.auth_error:
            st.markdown(f"""
            <div style="padding:12px 14px; background:#FFF5F5; border:1px solid #FEE2E2;
                        border-radius:8px; margin-bottom:16px; font-size:13px;
                        color:#DC2626; display:flex; align-items:center; gap:8px;">
              ⚠️ {st.session_state.auth_error}
            </div>
            """, unsafe_allow_html=True)

        # Input labels (styled as floating)
        st.markdown('<p style="font-size:13px; font-weight:500; color:#374151; margin:0 0 6px 0;">Work Email</p>', unsafe_allow_html=True)
        email = st.text_input("email", placeholder="you@company.com", key="signin_email", label_visibility="collapsed")

        st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin:14px 0 6px 0;"><p style="font-size:13px; font-weight:500; color:#374151; margin:0;">Password</p><a href="#" style="font-size:12px; color:#4A90FF; text-decoration:none;">Forgot password?</a></div>', unsafe_allow_html=True)
        password = st.text_input("password", type="password", placeholder="••••••••", key="signin_password", label_visibility="collapsed")

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        # Sign In button
        if st.button("Sign In", use_container_width=True, type="primary", key="signin_btn"):
            if not email or not password:
                st.session_state.auth_error = "Please enter your email and password."
                st.rerun()
            else:
                with st.spinner("Signing in..."):
                    success = sign_in(email, password)
                if success:
                    st.rerun()
                else:
                    st.rerun()

        # Switch to sign up
        st.markdown("""
            <p style="text-align:center; font-size:13px;
                      color:#6B7280; margin-top:20px;">
              Don't have an account?
            </p>
          </div><!-- end card -->
        </div>
        """, unsafe_allow_html=True)

        # Switch to signup button
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("Create an account →", use_container_width=True, key="goto_signup"):
                st.session_state.auth_page  = "signup"
                st.session_state.auth_error = ""
                st.rerun()


# ─────────────────────────────────────────
# SIGN UP PAGE UI
# ─────────────────────────────────────────

def render_sign_up():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
      html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background: #FFFFFF !important;
      }
      #MainMenu, footer, header { visibility: hidden; }
      .block-container { padding: 0 !important; max-width: 100% !important; }
      [data-testid="stTextInput"] input {
        height: 44px !important; border: 1.5px solid #E5E7EB !important;
        border-radius: 8px !important; font-size: 14px !important;
        padding: 0 14px !important; font-family: 'Inter', sans-serif !important;
        transition: border-color 0.15s ease !important;
      }
      [data-testid="stTextInput"] input:focus {
        border-color: #4A90FF !important;
        box-shadow: 0 0 0 3px rgba(74,144,255,0.12) !important;
      }
      [data-testid="stTextInput"] label { display: none !important; }
      [data-testid="stButton"] button {
        height: 44px !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 14px !important;
        font-family: 'Inter', sans-serif !important;
      }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("""
        <div style="min-height:100vh; display:flex; flex-direction:column;
                    justify-content:center; padding:60px 0;">

          <!-- Logo -->
          <div style="text-align:center; margin-bottom:32px;">
            <div style="display:inline-flex; align-items:center; gap:10px;">
              <div style="width:36px; height:36px; background:#0A0A0A;
                          border-radius:8px; display:flex; align-items:center;
                          justify-content:center;">
                <span style="color:white; font-weight:800; font-size:18px;">C</span>
              </div>
              <span style="font-size:22px; font-weight:800;
                           letter-spacing:-0.04em; color:#0A0A0A;">Calipr</span>
            </div>
            <h2 style="font-size:22px; font-weight:800; letter-spacing:-0.03em;
                       color:#0A0A0A; margin:20px 0 6px 0; text-align:center;">
              Create your account
            </h2>
            <p style="font-size:14px; color:#6B7280; margin:0; text-align:center;">
              Start ranking candidates in minutes
            </p>
          </div>

          <!-- PLAN SELECTOR — 3 cards -->
          <p style="font-size:13px; font-weight:600; color:#0A0A0A;
                    margin:0 0 12px 0;">Choose your plan</p>
        """, unsafe_allow_html=True)

        plan_options = ["free", "pro", "enterprise"]
        plan_labels  = {
            "free":       ("Starter",      "$0",    "/ forever",  "50 candidates, sample JD, 5-signal scoring"),
            "pro":        ("Professional", "$49",   "/ month",    "Unlimited candidates, recruiter memory, CSV export"),
            "enterprise": ("Enterprise",   "Custom", "",           "On-premise, ATS integration, bias audit reports"),
        }

        if "selected_plan" not in st.session_state:
            st.session_state.selected_plan = "pro"

        # Plan cards as columns
        p1, p2, p3 = st.columns(3, gap="small")
        plan_cols = {"free": p1, "pro": p2, "enterprise": p3}
        plan_border = {
            "free":       "#E5E7EB",
            "pro":        "#4A90FF",
            "enterprise": "#7C3AED",
        }
        plan_badge_bg = {
            "free":       "#F3F4F6",
            "pro":        "#EFF6FF",
            "enterprise": "#F5F3FF",
        }
        plan_badge_color = {
            "free":       "#6B7280",
            "pro":        "#4A90FF",
            "enterprise": "#7C3AED",
        }

        for plan_key, pcol in plan_cols.items():
            label, price, period, desc = plan_labels[plan_key]
            selected = st.session_state.selected_plan == plan_key
            border_w = "2px" if selected else "1px"
            border_c = plan_border[plan_key] if selected else "#E5E7EB"
            bg       = "#FAFEFF" if selected and plan_key == "pro" else "#FFFFFF"
            
            # Extract check indicator to avoid f-string escaping issues
            check_indicator = (
                '<div style="margin-top:12px; width:18px; height:18px; border-radius:50%; '
                'background:#4A90FF; display:flex; align-items:center; justify-content:center;">'
                '<span style="color:white; font-size:10px; font-weight:bold;">✓</span></div>'
                if selected else '<div style="height:30px;"></div>'
            )

            with pcol:
                st.markdown(f"""
                <div style="border:{border_w} solid {border_c}; border-radius:12px;
                            padding:16px 14px; background:{bg};
                            transition:all 0.15s ease; min-height:185px;
                            box-shadow:{'0 4px 12px rgba(74,144,255,0.12)' if selected else '0 1px 3px rgba(0,0,0,0.02)'};">
                  <span style="background:{plan_badge_bg[plan_key]}; color:{plan_badge_color[plan_key]};
                               font-size:10px; font-weight:700; padding:2px 8px;
                               border-radius:9999px; text-transform:uppercase;
                               letter-spacing:0.08em;">{label}</span>
                  <div style="margin-top:10px;">
                    <span style="font-size:22px; font-weight:900;
                                 letter-spacing:-0.04em; color:#0A0A0A;">{price}</span>
                    <span style="font-size:11px; color:#9CA3AF;
                                 margin-left:3px;">{period}</span>
                  </div>
                  <p style="font-size:11px; color:#6B7280; margin:8px 0 0 0;
                             line-height:1.4;">{desc}</p>
                  {check_indicator}
                </div>
                """, unsafe_allow_html=True)

                if st.button(
                    f"Select {label}",
                    key=f"plan_{plan_key}",
                    use_container_width=True,
                ):
                    st.session_state.selected_plan = plan_key
                    st.rerun()

        # Error message
        if st.session_state.auth_error:
            st.markdown(f"""
            <div style="padding:12px 14px; background:#FFF5F5; border:1px solid #FEE2E2;
                        border-radius:8px; margin:16px 0; font-size:13px; color:#DC2626;
                        display:flex; align-items:center; gap:8px;">
              ⚠️ {st.session_state.auth_error}
            </div>
            """, unsafe_allow_html=True)

        # Success message
        if st.session_state.auth_success:
            st.markdown(f"""
            <div style="padding:12px 14px; background:#F0FDF4; border:1px solid #BBF7D0;
                        border-radius:8px; margin:16px 0; font-size:13px; color:#16A34A;
                        display:flex; align-items:center; gap:8px;">
              ✅ {st.session_state.auth_success}
            </div>
            """, unsafe_allow_html=True)

        # Form fields container
        st.markdown("""
          <!-- Form card -->
          <div style="background:#FFFFFF; border:1px solid #F3F4F6; border-radius:16px;
                      padding:28px 24px; margin-top:16px;
                      box-shadow:0 4px 24px rgba(0,0,0,0.06);">
        """, unsafe_allow_html=True)

        st.markdown('<p style="font-size:13px; font-weight:500; color:#374151; margin:0 0 6px 0;">Full Name</p>', unsafe_allow_html=True)
        full_name = st.text_input("fn", placeholder="Aum Santoki", key="signup_name", label_visibility="collapsed")

        st.markdown('<p style="font-size:13px; font-weight:500; color:#374151; margin:14px 0 6px 0;">Work Email</p>', unsafe_allow_html=True)
        email = st.text_input("em", placeholder="you@company.com", key="signup_email", label_visibility="collapsed")

        col_p1, col_p2 = st.columns(2, gap="small")
        with col_p1:
            st.markdown('<p style="font-size:13px; font-weight:500; color:#374151; margin:14px 0 6px 0;">Password</p>', unsafe_allow_html=True)
            password = st.text_input("pw", type="password", placeholder="Min 8 chars", key="signup_password", label_visibility="collapsed")
        with col_p2:
            st.markdown('<p style="font-size:13px; font-weight:500; color:#374151; margin:14px 0 6px 0;">Confirm Password</p>', unsafe_allow_html=True)
            confirm  = st.text_input("cp", type="password", placeholder="Repeat password", key="signup_confirm", label_visibility="collapsed")

        # Password strength bar
        if password:
            strength = 0
            if len(password) >= 8:  strength += 1
            if any(c.isupper() for c in password): strength += 1
            if any(c.isdigit() for c in password): strength += 1
            if any(c in "!@#$%^&*" for c in password): strength += 1

            strength_colors = ["#EF4444", "#F59E0B", "#4A90FF", "#16A34A"]
            strength_labels = ["Weak", "Fair", "Good", "Strong"]
            sc = strength_colors[strength - 1] if strength > 0 else "#E5E7EB"
            sl = strength_labels[strength - 1] if strength > 0 else ""
            
            bars_html = "".join([
                f'<div style="flex:1; height:3px; border-radius:9999px; background:{(sc if i < strength else "#E5E7EB")};"></div>' 
                for i in range(4)
            ])
            
            st.markdown(f"""
            <div style="margin-top:8px;">
              <div style="display:flex; gap:4px; margin-bottom:4px;">
                {bars_html}
              </div>
              <span style="font-size:11px; color:{sc}; font-weight:500;">{sl}</span>
            </div>
            """, unsafe_allow_html=True)

        # Terms checkbox
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        terms = st.checkbox("I agree to the Terms of Service and Privacy Policy", key="signup_terms")

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        # Plan-aware CTA button label
        btn_labels = {
            "free":       "Get Started Free",
            "pro":        "Start Free Trial — Pro",
            "enterprise": "Contact Sales",
        }
        btn_label = btn_labels[st.session_state.selected_plan]

        if st.button(btn_label, use_container_width=True, type="primary", key="signup_btn"):
            if not full_name.strip():
                st.session_state.auth_error = "Please enter your full name."
                st.rerun()
            elif not email.strip():
                st.session_state.auth_error = "Please enter your email."
                st.rerun()
            elif not password:
                st.session_state.auth_error = "Please enter a password."
                st.rerun()
            elif len(password) < 8:
                st.session_state.auth_error = "Password must be at least 8 characters."
                st.rerun()
            elif password != confirm:
                st.session_state.auth_error = "Passwords do not match."
                st.rerun()
            elif not terms:
                st.session_state.auth_error = "Please accept the Terms of Service."
                st.rerun()
            else:
                st.session_state.auth_error = ""
                with st.spinner("Creating your account..."):
                    success = sign_up(
                        full_name=full_name.strip(),
                        email=email.strip(),
                        password=password,
                        plan=st.session_state.selected_plan,
                    )
                if success:
                    st.rerun()
                else:
                    st.rerun()

        st.markdown("""
          </div><!-- end form card -->
        """, unsafe_allow_html=True)

        # Back to sign in
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("← Back to Sign In", use_container_width=True, key="goto_signin"):
                st.session_state.auth_page  = "signin"
                st.session_state.auth_error = ""
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
# NAVBAR USER CARD RENDERING
# ─────────────────────────────────────────

def render_navbar_user():
    """
    Renders the user avatar, name, plan badge in the navbar.
    """
    plan         = st.session_state.get("user_plan", "free")
    name         = st.session_state.get("user_name", "User")
    initials     = st.session_state.get("user_initials", "?")

    plan_badge = {
        "free":       ("FREE",       "#6B7280", "#F3F4F6"),
        "pro":        ("PRO",        "#FFFFFF",  "#0A0A0A"),
        "enterprise": ("ENTERPRISE", "#7C3AED", "#F5F3FF"),
    }
    badge_label, badge_text, badge_bg = plan_badge.get(plan, plan_badge["free"])

    # Renders user initials, name and badge using inline HTML matching landing page layout
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; padding: 4px 12px; 
                background: #FFFFFF; border: 1px solid #F3F4F6; border-radius: 9999px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.02); margin-left: auto;">
      <!-- Plan badge -->
      <span style="background:{badge_bg}; color:{badge_text}; font-size:9px;
                   font-weight:800; padding:2px 7px; border-radius:9999px;
                   letter-spacing:0.06em;">{badge_label}</span>
      <!-- User avatar circle -->
      <div style="width:26px; height:26px; border-radius:50%;
                  background:#0A0A0A; display:flex; align-items:center;
                  justify-content:center;">
        <span style="color:white; font-size:11px; font-weight:700;">{initials}</span>
      </div>
      <!-- Name -->
      <span style="font-size:13px; font-weight:600; color:#0A0A0A; padding-right:4px;">{name}</span>
    </div>
    """, unsafe_allow_html=True)
