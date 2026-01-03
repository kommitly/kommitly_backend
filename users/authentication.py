from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("🔥 CookieJWTAuthentication CALLED")
        print("🍪 Cookies:", request.COOKIES)
        raw_token = request.COOKIES.get("access_token")

        if not raw_token:
            print("❌ No access_token cookie")
            return None


        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        print("✅ Authenticated user:", user)
        return (user, validated_token)
