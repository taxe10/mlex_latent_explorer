import asyncio
import logging
import os
import time

import numpy as np
from dotenv import load_dotenv
from tiled.client import from_uri

load_dotenv(".env")

DATA_TILED_URI = (
    "https://tiled-demo.blueskyproject.io/api/v1/metadata/rsoxs/raw/"
    "468810ed-2ff9-4e92-8ca9-dcb376d01a56/primary/data/Small Angle CCD Detector_image"
)
DATA_TILED_API_KEY = os.getenv("DATA_TILED_KEY")
if DATA_TILED_API_KEY == "":
    DATA_TILED_API_KEY = None

RESULTS_TILED_URI = os.getenv("RESULTS_TILED_URI", "")
# Only append "/api/v1/metadata/" if it's not already in the string
if "/api/v1/metadata/" not in RESULTS_TILED_URI:
    RESULTS_TILED_URI = RESULTS_TILED_URI.rstrip("/") + "/api/v1/metadata/"

RESULTS_TILED_API_KEY = os.getenv("RESULTS_TILED_API_KEY", None)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_num_frames(tiled_uri, tiled_api_key=None):
    client = from_uri(tiled_uri, api_key=tiled_api_key)
    return client.shape


def get_feature_vectors(num_messages):
    return 5 * np.random.rand(num_messages, 2)


async def stream():
    """
    Connect to the existing WebSocket server elsewhere,
    send messages, then close the connection.
    """

    logger.info("Preparing messages to send...")
    time.sleep(3)

    num_messages, c, x, y = get_num_frames(DATA_TILED_URI, DATA_TILED_API_KEY)
    feature_vector_list = get_feature_vectors(num_messages)

    # Connect to the server

    logger.info("Successfully connected to the server!")

    for index, latent_vector in zip(range(num_messages), feature_vector_list):
        message = {
            "tiled_url": f"{DATA_TILED_URI}?slice={index}",  # be compatible with LatentSpaceEvent
            "index": index,
            "feature_vector": latent_vector.tolist(),
        }
        logger.info(f"Sending message: {message}")

        # Send the message (as JSON) to the server
        yield message

        await asyncio.sleep(0.05)

    logger.info("All messages sent; connection closed.")
