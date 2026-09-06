import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

// Build-time provider configuration. When either is missing the corresponding
// button (and SDK) is simply not rendered, so local dev without credentials
// shows the classic password form only.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const FACEBOOK_APP_ID = import.meta.env.VITE_FACEBOOK_APP_ID || "";

function loadScript(src, id) {
  return new Promise((resolve, reject) => {
    if (document.getElementById(id)) return resolve();
    const s = document.createElement("script");
    s.src = src;
    s.id = id;
    s.async = true;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

function GoogleButton({ busy, disabled, onCredential }) {
  const divRef = useRef(null);
  const initializedRef = useRef(false);
  const onCredentialRef = useRef(onCredential);
  onCredentialRef.current = onCredential;

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || divRef.current === null) return;
    let cancelled = false;
    let resizeObserver = null;
    (async () => {
      try {
        await loadScript("https://accounts.google.com/gsi/client", "gsi-client");
        if (cancelled || !window.google?.accounts?.id) return;
        // Guard against multiple initializations
        if (initializedRef.current) return;
        initializedRef.current = true;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (res) => res?.credential && onCredentialRef.current(res.credential),
          auto_select: false,
          use_fedcm_for_prompt: true,
        });
        // Render at the container's width instead of a fixed 320px so the
        // button never overflows narrow mobile cards (Google only accepts
        // 200–400px, so clamp and re-render when the column resizes).
        let lastWidth = 0;
        const render = () => {
          const el = divRef.current;
          if (!el || !window.google?.accounts?.id) return;
          const width = Math.max(200, Math.min(400, el.offsetWidth || 320));
          if (width === lastWidth) return;
          lastWidth = width;
          window.google.accounts.id.renderButton(el, {
            theme: "outline",
            size: "large",
            width,
            text: "continue_with",
          });
        };
        render();
        resizeObserver = new ResizeObserver(render);
        resizeObserver.observe(divRef.current);
      } catch {
        // SDK blocked (ad-blocker / offline): fall back to the plain form.
      }
    })();
    return () => {
      cancelled = true;
      if (resizeObserver) resizeObserver.disconnect();
    };
  }, []);
  if (!GOOGLE_CLIENT_ID) return null;
  return <div ref={divRef} className={`w-full ${busy ? "pointer-events-none opacity-60" : ""}`} />;
}

function FacebookButton({ busy, disabled, onAccessToken }) {
  async function popupLogin() {
    if (!FACEBOOK_APP_ID) return;
    const redirect = window.location.origin + window.location.pathname;
    const url =
      "https://www.facebook.com/v19.0/dialog/oauth?client_id=" +
      encodeURIComponent(FACEBOOK_APP_ID) +
      "&redirect_uri=" +
      encodeURIComponent(redirect) +
      "&response_type=token&scope=email,public_profile";
    const win = window.open(url, "fb_login", "width=480,height=640");
    if (!win) return;
    const timer = setInterval(() => {
      try {
        const params = new URLSearchParams(win.location.hash.substring(1));
        const token = params.get("access_token");
        if (token) {
          clearInterval(timer);
          win.close();
          onAccessToken(token);
        } else if (win.closed) {
          clearInterval(timer);
        }
      } catch {
        // cross-origin while navigating facebook.com — keep polling
      }
    }, 400);
  }
  if (!FACEBOOK_APP_ID) return null;
  return (
    <button
      type="button"
      onClick={popupLogin}
      disabled={busy || disabled}
      className="btn-secondary w-full"
    >
      Continue with Facebook
    </button>
  );
}

export default function SocialLogin({ busy }) {
  const { loginWithSocial } = useAuth();
  const [error, setError] = useState("");
  const [waiting, setWaiting] = useState(false);

  async function finish(path, payload) {
    setError("");
    setWaiting(true);
    try {
      await loginWithSocial(path, payload);
    } catch (err) {
      setError(err.message || "Social sign-in failed");
    } finally {
      setWaiting(false);
    }
  }

  if (!GOOGLE_CLIENT_ID && !FACEBOOK_APP_ID) return null;
  const inFlight = busy || waiting;
  return (
    <>
      <div className="my-5 flex items-center gap-3">
        <span className="h-px flex-1 bg-ink-200" />
        <span className="text-xs font-medium uppercase tracking-wide text-ink-400">
          or
        </span>
        <span className="h-px flex-1 bg-ink-200" />
      </div>
      <div className="space-y-3">
        <GoogleButton
          busy={inFlight}
          disabled={false}
          onCredential={(c) => finish("/api/v1/auth/google", { credential: c })}
        />
        <FacebookButton
          busy={inFlight}
          disabled={false}
          onAccessToken={(t) => finish("/api/v1/auth/facebook", { access_token: t })}
        />
      </div>
      {error && <div className="alert alert-error mt-4">{error}</div>}
    </>
  );
}
