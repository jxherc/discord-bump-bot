import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

import aiohttp
import discord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

DISBOARD_ID = 302050872383242240
EST = timezone(timedelta(hours=-5))

client = discord.Client()


async def do_bump():
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        channel = await client.fetch_channel(CHANNEL_ID)

    guild = channel.guild

    try:
        cached = await guild.application_commands()
    except TypeError:
        cached = guild.application_commands()

    bump = next(
        (c for c in cached if c.name == "bump" and getattr(c, "application_id", None) == DISBOARD_ID),
        None,
    ) or next((c for c in cached if c.name == "bump"), None)

    if not bump:
        logger.error("No /bump command found.")
        return False

    cmd_id = str(bump.id)
    cmd_version = str(bump.version)

    nonce = str(random.randint(100000000000000000, 999999999999999999))
    payload = {
        "type": 2,
        "application_id": str(DISBOARD_ID),
        "guild_id": str(guild.id),
        "channel_id": str(channel.id),
        "session_id": client.ws.session_id,
        "nonce": nonce,
        "data": {
            "version": cmd_version,
            "id": cmd_id,
            "name": "bump",
            "type": 1,
            "options": [],
            "attachments": [],
        },
    }

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post("https://discord.com/api/v9/interactions", json=payload) as resp:
            if resp.status == 204:
                logger.info("Bumped at %s", datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S EST"))
                return True
            text = await resp.text()
            logger.error("Bump failed: %s %s", resp.status, text)
            return False


async def bump_loop():
    await client.wait_until_ready()
    logger.info("Logged in as %s", client.user)

    while not client.is_closed():
        try:
            await do_bump()
        except Exception as exc:
            logger.error("Bump error: %s", exc)

        interval = random.randint(120 * 60, 130 * 60)
        next_time = datetime.now(EST) + timedelta(seconds=interval)
        logger.info(
            "Next bump at %s (%dm %ds)",
            next_time.strftime("%Y-%m-%d %H:%M:%S EST"),
            interval // 60,
            interval % 60,
        )
        await asyncio.sleep(interval)


@client.event
async def on_ready():
    asyncio.ensure_future(bump_loop())


client.run(TOKEN)
