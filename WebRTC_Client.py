import asyncio
import logging
import json
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaPlayer, MediaRelay
from aiortc.contrib.signaling import BYE

logger = logging.getLogger("client")

class WebRTC_Client:
    def __init__(self, signaling, room_name, media_path=None):
        """
        Initialize the WebRTC_Client.
        
        :param signaling: A signaling object for communication with the server.
        :param room_name: Name of the room to join.
        :param media_path: Path to a local media file for testing (optional).
        """
        self.signaling = signaling
        self.room_name = room_name
        self.pc = RTCPeerConnection()
        self.media_path = media_path
        self.relay = MediaRelay()

    async def connect(self):
        """
        Establish a WebRTC connection to the server.
        """
        # Prepare media sources
        if self.media_path:
            self.player = MediaPlayer(self.media_path)
        else:
            self.player = None

        @self.pc.on("track")
        async def on_track(track):
            """
            Handle incoming tracks from the server.
            """
            logger.info("Track %s received", track.kind)
            if track.kind == "audio":
                logger.info("Playing incoming audio track")
            elif track.kind == "video":
                logger.info("Displaying incoming video track")

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            """
            Handle incoming data channels.
            """
            logger.info("Data channel opened")

            @channel.on("message")
            def on_message(message):
                """
                Handle incoming messages.
                """
                logger.info("Received message: %s", message)

        # Connect to the signaling server
        await self.signaling.connect()

        # Create an offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)

        # Send the offer to the server
        message = {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type,
        }
        await self.signaling.send(json.dumps(message))

        # Wait for the answer
        response = await self.signaling.receive()
        params = json.loads(response)
        answer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        await self.pc.setRemoteDescription(answer)

    async def send_text_message(self, message):
        """
        Send a text message to the room via a data channel.
        """
        if not hasattr(self, "data_channel"):
            self.data_channel = self.pc.createDataChannel("chat")
            logger.info("Data channel created")

        if self.data_channel.readyState == "open":
            self.data_channel.send(message)
            logger.info("Sent message: %s", message)
        else:
            logger.error("Data channel is not open")

    async def close(self):
        """
        Close the WebRTC connection.
        """
        await self.pc.close()
        await self.signaling.close()
        logger.info("Connection closed")

    async def run(self):
        """
        Run the client to connect to the server and handle user input.
        """
        await self.connect()

        # Handle user input for sending text messages
        print("Type 'bye' to exit.")
        while True:
            message = input("Enter message: ")
            if message.lower() == "bye":
                break
            await self.send_text_message(message)

        # Close the connection
        await self.close()
