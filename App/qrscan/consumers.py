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
        try: 
            # Receive QR code from the WebSocket
            text_data_json = json.loads(text_data)
            print(text_data_json.get('eventid'))
            qr_code = text_data_json.get('qr_code')
            eventid = text_data_json.get('eventid')
            # report##########
            action = text_data_json.get('action')
            if action == 'fetch_report' and eventid:
                report = await self.fetch_report(eventid)
                await self.send(text_data=json.dumps({
                    'action': 'report',
                    'report': report
                }))
                return
            #######################
            # Process the QR code (e.g., validate it)
            # You can also interact with the database or perform any task here.
            if not qr_code or not eventid:
                # if missing, just send an error message but keep the socket open
                await self.send(text_data=json.dumps({
                    'action': 'error',
                    'message': 'Missing qr_code or eventid'
                }))
                return
            
            print(qr_code['decodedText'])
            if qr_code:
                # Check if the QR code already exists in the database
                existing_qr = await self.query_qr_code(qr_code,eventid)
                print(existing_qr)
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
                'message': response_message
            }))

        except Exception as e:
            # catch *any* error, send it back as a WS message, but do NOT close the socket
            await self.send(text_data=json.dumps({
                'action': 'error',
                'message': str(e)
            }))
            # optionally log:
            print("WebSocket error:", e)
    @sync_to_async
    def query_qr_code(self, qr_code, eventid):
        with connection.cursor() as cursor:
            # Example raw SQL query
            # cursor.execute("SELECT * FROM qrcodes_qrcode WHERE data = %s", [qr_code['decodedText']])
            # result = cursor.fetchone()
            cursor.execute("""
                SELECT 1
                FROM qrcodes_event_qr_codes AS ec
                JOIN qrcodes_qrcode AS qr ON ec.qrcode_id = qr.id
                WHERE ec.event_id = %s AND qr.data = %s
                LIMIT 1
            """, [str(eventid), qr_code['decodedText']])
            result = cursor.fetchone() is not None
            print(result)
            if result is None:
                return None  # Return None if no result is found
            if result:
                cursor.execute("SELECT * FROM qrcodes_qrcode WHERE data = %s", [qr_code['decodedText']])
                result2 = cursor.fetchone()
                if result2[7]=='nuevo':
                # Si el QR existe, actualizar su estado a "concedido"
                    print('actualizado')
                    # cursor.execute("UPDATE qrcodes_qrcode SET status_scan = %s WHERE data = %s", ["concedido", qr_code['decodedText']])
                    cursor.execute(
                    "UPDATE qrcodes_qrcode SET status_scan = %s, updated_at = NOW() WHERE data = %s",
                    ["concedido", qr_code['decodedText']]
                    )
                return result2
            
        return None
    
    # @sync_to_async
    # def fetch_report(self, eventid):
            
    #     from qrcodes.models import QRCode, Event   # ← lazy import
    #     # Last 5 conceded
    #     last5 = list(
    #         QRCode.objects
    #               .filter(event_fk__id=eventid, status_scan='concedido')
    #               .order_by('-updated_at')
    #               .values('data', 'updated_at')[:5]
    #     )
    #     # Counts
    #     total = QRCode.objects.filter(event_fk__id=eventid, status_scan__in=['nuevo','concedido']).count()
    #     conceded = QRCode.objects.filter(event_fk__id=eventid, status_scan='concedido').count()
    #     nuevo = total - conceded
    #     return {
    #         'last5': [
    #             {'data': r['data'], 'updated_at': r['updated_at'].isoformat()}
    #             for r in last5
    #         ],
    #         'counts': {'nuevo': nuevo, 'concedido': conceded}
    #     }
    @sync_to_async
    def fetch_report(self, eventid):
        with connection.cursor() as cursor:
            # 1) Last 5 conceded scans
            cursor.execute("""
                SELECT qp.data, qp.updated_at
                  FROM qrcodes_event_qr_codes ec
                  JOIN qrcodes_qrcode qp
                    ON ec.qrcode_id = qp.id
                 WHERE ec.event_id = %s
                   AND qp.status_scan = 'concedido'
                 ORDER BY qp.updated_at DESC
                 LIMIT 5
            """, [str(eventid)])
            rows = cursor.fetchall()
            last5 = [
                {'data': data, 'updated_at': updated_at.isoformat()}
                for data, updated_at in rows
            ]

            # 2) Counts of nuevo vs concedido
            cursor.execute("""
                SELECT
                  SUM(CASE WHEN qp.status_scan = 'nuevo' THEN 1 ELSE 0 END)   AS nuevo_count,
                  SUM(CASE WHEN qp.status_scan = 'concedido' THEN 1 ELSE 0 END) AS concedido_count
                  FROM qrcodes_event_qr_codes ec
                  JOIN qrcodes_qrcode qp
                    ON ec.qrcode_id = qp.id
                 WHERE ec.event_id = %s
            """, [str(eventid)])
            nuevo_count, concedido_count = cursor.fetchone()

        return {
            'last5': last5,
            'counts': {
                'nuevo':   nuevo_count   or 0,
                'concedido': concedido_count or 0
            }
        }