import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import connection

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
        print(qr_code['decodedText'])
        if qr_code:
            # Check if the QR code already exists in the database
            existing_qr = await self.query_qr_code(qr_code)
            print(existing_qr.status_scan)
            if existing_qr:
                # If QR code exists, send a response back that it's already processed
                response_message = f'QR code already processed successfully'
            else:
                response_message = "The QR code you scanned is invalid or does not exist."

        # Send response back to the WebSocket client
        await self.send(text_data=json.dumps({
            # 'message': f'QR code {qr_code} processed successfully!'
            'message': response_message
        }))
    @sync_to_async
    def query_qr_code(self, qr_code):
        with connection.cursor() as cursor:
            # Example raw SQL query
            cursor.execute("SELECT * FROM qrcodes_qrcode WHERE data = %s", [qr_code['decodedText']])
            result = cursor.fetchone()
        return result