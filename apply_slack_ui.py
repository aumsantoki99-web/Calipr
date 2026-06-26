import os

with open("hf_space_clone/integrations_ui.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_ui_code = """            import os
            import datetime
            from slack_notifier import send_test_notification

            SANDBOX_URL = "https://huggingface.co/spaces/Aumus/calipr"
            slack_configured = bool(os.environ.get("SLACK_WEBHOOK_URL", ""))

            # Last notification time (store in session state after each send)
            if "slack_last_sent" not in st.session_state:
                st.session_state.slack_last_sent = None
            if "slack_test_status" not in st.session_state:
                st.session_state.slack_test_status = None   # None | "success" | "error"

            # ── CARD HTML ──
            status_html = ""
            if slack_configured:
                last_sent = st.session_state.slack_last_sent
                last_sent_str = (
                    f"Last sent: {last_sent}" if last_sent
                    else "Connected · Waiting for first ranking run"
                )
                status_html = f'''
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
                  <span style="display:inline-block; width:8px; height:8px; border-radius:50%;
                               background:#16A34A; animation: pulse 2s ease-in-out infinite;"></span>
                  <span style="font-size:13px; color:#16A34A; font-weight:600;">CONNECTED</span>
                  <span style="font-size:12px; color:#9CA3AF; margin-left:4px;">· {last_sent_str}</span>
                </div>
                '''
                card_border = "border-top: 3px solid #0D9488;"
            else:
                status_html = '''
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
                  <span style="display:inline-block; width:8px; height:8px;
                               border-radius:50%; background:#9CA3AF;"></span>
                  <span style="font-size:13px; color:#9CA3AF; font-weight:600;">NOT CONNECTED</span>
                </div>
                '''
                card_border = "border-top: 3px solid #E5E7EB;"

            st.markdown(f'''
            <div style="background:#FFFFFF; border:1px solid #F3F4F6; {card_border}
                        border-radius:12px; padding:24px; margin-bottom:16px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.06);">

              <!-- Header row -->
              <div style="display:flex; align-items:center; gap:14px; margin-bottom:16px;">
                <!-- Slack logo SVG inline -->
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                  <rect width="32" height="32" rx="8" fill="#4A154B"/>
                  <path d="M11 18.5a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm1.5-4.5H9a2 2 0 1 0 0 4h3.5V14z"
                        fill="#E01E5A"/>
                  <path d="M13.5 11a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm-4.5 1.5v-3.5a2 2 0 1 0-4 0v3.5h4z"
                        fill="#36C5F0"/>
                  <path d="M21 13.5a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm-1.5 4.5H23a2 2 0 1 0 0-4h-3.5V18z"
                        fill="#2EB67D"/>
                  <path d="M18.5 21a2 2 0 1 1 0 4 2 2 0 0 1 0-4zm4.5-1.5v3.5a2 2 0 1 0 4 0v-3.5h-4z"
                        fill="#ECB22E"/>
                </svg>
                <div>
                  <div style="font-size:16px; font-weight:700; color:#0A0A0A;">Slack</div>
                  <div style="font-size:12px; color:#6B7280;">
                    Send ranked shortlists to your #recruiting channel instantly
                  </div>
                </div>
                <span style="margin-left:auto; font-size:11px; font-weight:600;
                             padding:3px 10px; border-radius:9999px;
                             background:{'#DCFCE7' if slack_configured else '#F3F4F6'};
                             color:{'#16A34A' if slack_configured else '#6B7280'};
                             border:1px solid {'#BBF7D0' if slack_configured else '#E5E7EB'};">
                  {'CONNECTED' if slack_configured else 'AVAILABLE'}
                </span>
              </div>

              <!-- Status -->
              {status_html}

              <!-- What it does -->
              <div style="font-size:13px; color:#374151; line-height:1.7; margin-bottom:20px;">
                After every ranking run, Calipr automatically posts the
                <strong>Top 5 candidates</strong> to your Slack channel with:
                full signal breakdown, pipeline runtime, Precision@5 score,
                and a direct link back to the sandbox.
              </div>

              <!-- Setup instruction if not connected -->
              {'<div style="padding:12px 16px; background:#F8FAFC; border:1px solid #F3F4F6; border-radius:8px; font-size:12px; color:#6B7280; margin-bottom:16px;"><strong style="color:#0A0A0A;">Setup:</strong> Add <code style="background:#F3F4F6; padding:2px 6px; border-radius:4px;">SLACK_WEBHOOK_URL</code> to your HuggingFace Space secrets &rarr; Settings &rarr; Repository secrets.</div>' if not slack_configured else ''}

            </div>
            '''

            st.markdown(html_str, unsafe_allow_html=True)

            # ── ACTION BUTTONS ──
            if slack_configured:
                col_test, col_disconnect = st.columns([1, 1], gap="small")

                with col_test:
                    if st.button("📨 Test Slack Notification", use_container_width=True, type="primary"):
                        with st.spinner("Sending to Slack..."):
                            result = send_test_notification(SANDBOX_URL)
                        if result.get("success"):
                            st.session_state.slack_last_sent = datetime.datetime.now().strftime("%b %d at %I:%M %p")
                            st.session_state.slack_test_status = "success"
                            
                            # Add to activity log
                            if "activity_log" not in st.session_state:
                                st.session_state.activity_log = []
                            st.session_state.activity_log.insert(0, {
                                "icon": "💬",
                                "text": f"Sent top 5 candidates for <strong>Senior AI Engineer</strong> to <strong>#recruiting</strong>",
                                "meta": datetime.datetime.now().strftime("%I:%M %p · Just now"),
                                "color": "#4A154B",
                            })
                            
                            st.success("✅ Message sent! Check your #recruiting channel.")
                            st.rerun()
                        else:
                            st.session_state.slack_test_status = "error"
                            st.error(f"Failed: {result.get('error', 'Unknown error')}")

                with col_disconnect:
                    if st.button("Disconnect", use_container_width=True):
                        st.info("To disconnect, remove SLACK_WEBHOOK_URL from HuggingFace Space secrets.")

            else:
                st.markdown('''
                <a href="https://api.slack.com/messaging/webhooks" target="_blank"
                   style="display:inline-flex; align-items:center; gap:8px;
                          padding:10px 20px; background:#0A0A0A; color:#FFFFFF;
                          border-radius:8px; font-size:14px; font-weight:600;
                          text-decoration:none; transition:background 0.15s ease;">
                  Set Up Slack Integration ↗
                </a>
                ''', unsafe_allow_html=True)"""

# I need to adjust the way I render the f-string inside the f-string because it's difficult to properly escape in Python without breaking things.
# I will use string concatenation.

# Find lines 1039 to 1078 to replace
start_idx = 1039 # line 1040 is index 1039
end_idx = 1077 # line 1078 is index 1077

with open("hf_space_clone/integrations_ui.py", "w", encoding="utf-8") as f:
    f.writelines(lines[:start_idx])
    f.write(new_ui_code.replace("html_str", "f'''" + "..." + "'''") + "\n") # Wait this is broken, let me just fix the script.

    # I'll just write it correctly.
