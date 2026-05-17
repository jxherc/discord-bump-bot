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
    logger.info("Channel: %s | Guild: %s (ID: %s)", channel, guild, getattr(guild, "id", None))

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        # Find /bump command in this guild
        async with session.get(
            f"https://discord.com/api/v9/guilds/{guild.id}/application-commands/search",
            params={"type": 1, "query": "bump"},
        ) as resp:
            logger.info("Search response status: %s", resp.status)
            data = await resp.json()
            logger.info("Search response: %s", data)

        cmds = data.get("application_commands", [])
        logger.info("Commands found: %s", [c["name"] for c in cmds])

        bump = next(
            (c for c in cmds if c["name"] == "bump" and int(c["application_id"]) == DISBOARD_ID),
            None,
        )
        # Fallback: any bump command
        if not bump:
            bump = next((c for c in cmds if c["name"] == "bump"), None)

        if not bump:
            logger.error("No /bump command found. Commands: %s", cmds)
            return False

        nonce = str(random.randint(100000000000000000, 999999999999999999))
        payload = {
            "type": 2,
            "application_id": str(DISBOARD_ID),
            "guild_id": str(guild.id),
            "channel_id": str(channel.id),
            "session_id": client.ws.session_id,
            "nonce": nonce,
            "data": {
                "version": bump["version"],
                "id": bump["id"],
                "name": "bump",
                "type": 1,
                "options": [],
                "attachments": [],
            },
        }

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
            logger.error("Bump failed: %s", exc)

        interval = random.randint(120, 130) * 60
        next_time = datetime.now(EST) + timedelta(seconds=interval)
        logger.info(
            "Next bump at %s (%d min)",
            next_time.strftime("%Y-%m-%d %H:%M:%S EST"),
            interval // 60,
        )
        await asyncio.sleep(interval)


@client.event
async def on_ready():
    asyncio.ensure_future(bump_loop())


client.run(TOKEN)
