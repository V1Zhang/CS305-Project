import argparse
import asyncio
import json
import logging
import os
import ssl
import uuid

import cv2
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder, MediaRelay
from av import VideoFrame

logger = logging.getLogger("pc")

class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self, track, transform):
        super().__init__()  # don't forget this!
        self.track = track
        self.transform = transform

    async def recv(self):
        frame = await self.track.recv()

        if self.transform == "cartoon":
            img = frame.to_ndarray(format="bgr24")

            # prepare color
            img_color = cv2.pyrDown(cv2.pyrDown(img))
            for _ in range(6):
                img_color = cv2.bilateralFilter(img_color, 9, 9, 7)
            img_color = cv2.pyrUp(cv2.pyrUp(img_color))

            # prepare edges
            img_edges = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            img_edges = cv2.adaptiveThreshold(
                cv2.medianBlur(img_edges, 7),
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                9,
                2,
            )
            img_edges = cv2.cvtColor(img_edges, cv2.COLOR_GRAY2RGB)

            # combine color and edges
            img = cv2.bitwise_and(img_color, img_edges)

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        elif self.transform == "edges":
            # perform edge detection
            img = frame.to_ndarray(format="bgr24")
            img = cv2.cvtColor(cv2.Canny(img, 100, 200), cv2.COLOR_GRAY2BGR)

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        elif self.transform == "rotate":
            # rotate image
            img = frame.to_ndarray(format="bgr24")
            rows, cols, _ = img.shape
            M = cv2.getRotationMatrix2D((cols / 2, rows / 2), frame.time * 45, 1)
            img = cv2.warpAffine(img, M, (cols, rows))

            # rebuild a VideoFrame, preserving timing information
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base
            return new_frame
        else:
            return frame

class WebRTC_Server:
    def __init__(self):
        self.ip_address = "127.0.0.1"
        self.ip_port = 8080
        self.rooms = {} # Dictionary to store rooms
        self.clients = set() # Set to store all connected clients
        self.relay = MediaRelay()
        self.pcs = set()

    def create_room(self,room_name):
        # TODO: How to support multiple rooms?
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
            logger.info(f"Room {room_name} created")
        return self.rooms[room_name]
    
    def add_client_to_room(self,room_name,client_id,pc):
        if room_name in self.rooms:
            self.rooms[room_name].add((client_id,pc))
            logger.info(f"Client {client_id} added to room {room_name}")
        else:
            logger.error(f"Room {room_name} does not exist")
    
    def remove_client_from_room(self,room_name,client_id,pc):
        if room_name in self.rooms:
            self.rooms[room_name].remove((client_id,pc))
            logger.info(f"Client {client_id} removed from room {room_name}")
        else:
            logger.error(f"Room {room_name} does not exist")

    async def forward_message_to_room(self,room_name,message):
        """Forwards a message to all clients in the room."""
        ## TODO: Implement this function

    async def forward_media_to_room(self,room_name,track,transform=None):
        """Forwards a media track to all clients in the room."""
        ## TODO：Implement this function
    
    async def handle_offer(self,request,room_name):
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        client_id = str(uuid.uuid4())
        pc = RTCPeerConnection()
        pc_id = f"PeerConnection({client_id})"
        self.clients.add((client_id,pc))
        self.pcs.add(pc)
        self.add_client_to_room(room_name,client_id,pc)

        def log_info(msg, *args):
            logger.info(pc_id + " " + msg, *args)
        
        log_info("Created for %s", request.remote)

        # Prepare media
        recorder = MediaBlackhole()
        

        @pc.on("datachannel")
        def on_datachannel(channel):
        # TODO: Deliver the data channel message to the room
            @channel.on("message")
            def on_message(message):
                if isinstance(message, str) and message.startswith('ping'):
                    channel.send('pong' + message[4:])

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            log_info("Connection state is %s", pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)
                self.remove_client_from_room(room_name,client_id,pc)

        @pc.on("track")
        # TODO: Deliver the track to all the clients in the room
        def on_track(track):
            log_info("Track %s received", track.kind)

            if track.kind == "audio":
                # pc.addTrack(player.audio)
                recorder.addTrack(track)
            elif track.kind == "video":
                self.forward_media_to_room(room_name, track, transform=params["video_transform"])
                recorder.addTrack(self.relay.subscribe(track))

            @track.on("ended")
            async def on_ended():
                log_info("Track %s ended", track.kind)
                await recorder.stop()
        
        # Handle the offer
        await pc.setRemoteDescription(offer)
        await recorder.start()

        # send answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
