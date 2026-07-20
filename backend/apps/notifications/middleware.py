import re
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import AuditLog

class AuditLogMiddleware:
    SAFE = {"GET", "HEAD", "OPTIONS"}
    SKIP = ("/api/auth/token/", "/api/schema/", "/api/docs/")
    def __init__(self, get_response): self.get_response=get_response
    def __call__(self, request):
        response=self.get_response(request)
        if request.method not in self.SAFE and not request.path.startswith(self.SKIP):
            user=getattr(request,"user",None)
            if not getattr(user,"is_authenticated",False):
                try:
                    authenticated=JWTAuthentication().authenticate(request)
                    user=authenticated[0] if authenticated else None
                except Exception: user=None
            if getattr(user,"is_authenticated",False):
                segments=[part for part in request.path.strip("/").split("/") if part]
                target_id=next((part for part in reversed(segments) if re.fullmatch(r"\d+",part)),"")
                target_type=segments[1] if len(segments)>1 else ""
                AuditLog.objects.create(actor=user,actor_email=user.email,method=request.method,path=request.path[:500],action=f"{request.method} {target_type}",target_type=target_type,target_id=target_id,status_code=response.status_code,ip_address=request.META.get("REMOTE_ADDR") or None,user_agent=request.META.get("HTTP_USER_AGENT","")[:500],metadata={"query":request.META.get("QUERY_STRING","")[:500]})
        return response
