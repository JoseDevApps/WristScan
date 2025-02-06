import json
from channels.generic.websocket import AsyncWebsocketConsumer

class QRConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Close the WebSocket connection
        pass

    async def receive(self, text_data):
        # Receive QR code from the WebSocket
        text_data_json = json.loads(text_data)
        qr_code = text_data_json.get('qr_code')

        # Process the QR code (e.g., validate it)
        # You can also interact with the database or perform any task here.

        # Send response back to the WebSocket client
        await self.send(text_data=json.dumps({
            'message': f'QR code {qr_code} processed successfully!'
        }))