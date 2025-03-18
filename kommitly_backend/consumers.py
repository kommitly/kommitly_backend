from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import json
class VerificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope["url_route"]["kwargs"]["token"]
        self.user = await sync_to_async(User.objects.filter(verification_token=self.token).first)()

        await self.accept()

        if self.user:
            await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
            
            # ✅ If already verified, send an immediate response
            if self.user.is_verified:
                await self.send(text_data=json.dumps({"verified": True, "message": "Already verified"}))

    async def disconnect(self, close_code):
        if self.user:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

    async def user_verified(self, event):
        # ✅ Ensure correct message format
        await self.send(text_data=json.dumps({
            "verified": event["verified"],
            "message": event["message"]
        }))
