import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import connection
from datetime import datetime, timezone, timedelta

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
            print(existing_qr)
            print(existing_qr[7])
            if existing_qr:
                if existing_qr[7]=='nuevo':
                # If QR code exists, send a response back that it's already processed
                    response_message = f'QR - {existing_qr[0]} ingreso concedido'
                if existing_qr[7]=='concedido':
                    date = existing_qr[8].astimezone(timezone(timedelta(hours=-4))).strftime('%Y-%m-%d %H:%M:%S')
                    response_message = f'QR - {existing_qr[0]} - {date}'

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

            if result[7]=='nuevo':
            # Si el QR existe, actualizar su estado a "concedido"
                print('actualizado')
                # cursor.execute("UPDATE qrcodes_qrcode SET status_scan = %s WHERE data = %s", ["concedido", qr_code['decodedText']])
                cursor.execute(
                "UPDATE qrcodes_qrcode SET status_scan = %s, updated_at = NOW() WHERE data = %s",
                ["concedido", qr_code['decodedText']]
                )
            else:
                return None  # Si qr_code es None o no contiene 'decodedText', retorna None
            
        return result