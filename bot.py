import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.http import Route

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

    # Search for Disboard's /bump command in this guild
    data = await client.http.request(
        Route("GET", "/guilds/{guild_id}/application-commands/search", guild_id=guild.id),
        params={"type": 1, "query": "bump", "limit": 1, "application_id": DISBOARD_ID},
    )

    cmds = data.get("application_commands", [])
    bump = next((c for c in cmds if c["name"] == "bump"), None)

    if not bump:
        logger.error("Could not find /bump command — is Disboard in this server?")
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

    await client.http.request(Route("POST", "/interactions"), json=payload)
    logger.info("Bumped at %s", datetime.now(EST).strftime("%Y-%m-%d %H:%M:%S EST"))
    return True


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
