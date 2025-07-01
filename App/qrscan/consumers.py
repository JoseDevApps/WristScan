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
        eventid = text_data_json.get('eventid')
        # Process the QR code (e.g., validate it)
        # You can also interact with the database or perform any task here.
        print(qr_code['decodedText'])
        if qr_code:
            # Check if the QR code already exists in the database
            existing_qr = await self.query_qr_code(qr_code, eventid)

            if existing_qr is not None:
                if existing_qr[7]=='nuevo':
                # If QR code exists, send a response back that it's already processed
                    response_message = f'APROVADO'
                if existing_qr[7]=='concedido':
                    date = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-4))) - existing_qr[8].astimezone(timezone(timedelta(hours=-4)))
                    print(date)
                    hours, remainder = divmod(date.total_seconds(), 3600)
                    minutes, _ = divmod(remainder, 60)
                    response_message = f'DUPLICADO - escaneado hace:\n{hours} horas y {minutes} minutos'

            else:
                response_message = "DENEGADO"

        # Send response back to the WebSocket client
        await self.send(text_data=json.dumps({
            # 'message': f'QR code {qr_code} processed successfully!'
            'message': response_message
        }))
    @sync_to_async
    def query_qr_code(self, qr_code, eventid):
        with connection.cursor() as cursor:
            # Example raw SQL query
            # cursor.execute("SELECT * FROM qrcodes_qrcode WHERE data = %s", [qr_code['decodedText']])
            # result = cursor.fetchone()
            cursor.execute("""
                            SELECT 1
                            FROM qrcodes_qrcode q
                            INNER JOIN qrcodes_event_qr_codes eq
                                ON q.id = eq.qrcode_id
                            WHERE q.data = %s AND eq.event_id = %s
                            LIMIT 1
                        """, [qr_code, eventid])   
            result = cursor.fetchone() is not None

            if result is None:
                return None  # Return None if no result is found
            if result[7]=='nuevo':
            # Si el QR existe, actualizar su estado a "concedido"
                print('actualizado')
                # cursor.execute("UPDATE qrcodes_qrcode SET status_scan = %s WHERE data = %s", ["concedido", qr_code['decodedText']])
                cursor.execute(
                "UPDATE qrcodes_qrcode SET status_scan = %s, updated_at = NOW() WHERE data = %s",
                ["concedido", qr_code['decodedText']]
                )
            
        return result