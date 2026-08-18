async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    from_email: Optional[str] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """Send an email via the Resend HTTP API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        from_email: Optional sender email (defaults to SENDER_EMAIL)
        attachments: Optional list of Resend-compatible attachment dicts.
            Each dict may contain ``filename`` plus either ``content`` (base64
            string), ``path`` (public URL), or ``url``.

    Returns:
        dict with status and error details
    """
    result = {"status": "skipped", "error": None}

    if not _is_email_configured():
        result["error"] = "email_not_configured"
        logger.error("[email] delivery skipped | reason=RESEND_API_KEY missing")
        return result

    try:
        api_key = os.getenv("RESEND_API_KEY")
        sender = os.getenv("SENDER_EMAIL")
        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        if html_body:
            payload["html"] = html_body
        if attachments:
            payload["attachments"] = attachments

        logger.info(
            "[email] Resend delivery started | recipient=%s subject=%s",
            to_email,
            subject.encode("ascii", "ignore").decode("ascii") or subject,
        )
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
        result["status"] = "sent"
        logger.info("[email] Resend delivery completed | recipient=%s", to_email)
        return result
    
    except httpx.HTTPError as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.error("[email] Resend HTTP delivery failed | recipient=%s error=%s", to_email, exc)
        return result