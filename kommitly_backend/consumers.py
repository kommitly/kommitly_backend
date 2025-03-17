import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import User  # Import your User model
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

class VerificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.token = self.scope["url_route"]["kwargs"]["token"]
        logger.debug(f"WebSocket connect, token: {self.token}") #add logging
        await self.accept()
        await self.verify_and_send()

    async def verify_and_send(self):
        try:
            logger.debug(f"Attempting to get user with token: {self.token}") #add logging
            user = await sync_to_async(User.objects.get)(verification_token=self.token)
            logger.debug(f"User retrieved: {user}") #add logging
            if user.is_verified:
                logger.debug(f"User already verified: {user}") #add logging
                await self.send(text_data=json.dumps({"verified": True, "message": "Already verified"}))
            else:
                logger.debug(f"Verifying user: {user}") #add logging
                user.is_verified = True
                user.verification_token = None
                await sync_to_async(user.save)()
                logger.debug(f"User verified and saved: {user}") #add logging
                await self.send(text_data=json.dumps({"verified": True, "message": "Verified"}))

        except User.DoesNotExist:
            logger.debug(f"User with token {self.token} not found") #add logging
            await self.send(text_data=json.dumps({"verified": False, "message": "Invalid token"}))

        await self.close() # Close the connection after verification.