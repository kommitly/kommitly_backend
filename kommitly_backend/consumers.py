import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import User  # Import your User model
from asgiref.sync import sync_to_async

class VerificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope["url_route"]["kwargs"]["token"]
        await self.accept()
        await self.verify_and_send()

    async def verify_and_send(self):
        try:
            user = await sync_to_async(User.objects.get)(verification_token=self.token)
            if user.is_verified:
                await self.send(text_data=json.dumps({"verified": True, "message": "Already verified"}))
            else:
                user.is_verified = True
                user.verification_token = None
                await sync_to_async(user.save)()
                await self.send(text_data=json.dumps({"verified": True, "message": "Verified"}))

        except User.DoesNotExist:
            await self.send(text_data=json.dumps({"verified": False, "message": "Invalid token"}))

        await self.close() # Close the connection after verification.