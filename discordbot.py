# -*- coding: utf-8 -*-
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("環境変数が足りません")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

PROMPT = (
    "あなたは日本語の会議議事録を要約するアシスタントです。"
    "箇条書きで3〜7点、決定事項・TODO・保留を分けて短くまとめてください。"
)

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
    except Exception as e:
        print("tree sync error:", e)
    print(f"ready: {bot.user}")

@bot.tree.command(name="summarize", description="直近のメッセージを要約（デフォ50件）")
@app_commands.describe(limit="何件分まとめるか（10〜200）")
async def summarize(inter: discord.Interaction, limit: int = 50):
    if not (10 <= limit <= 200):
        await inter.response.send_message("10〜200件の間にして下さい", ephemeral=True)
        return
    await inter.response.defer(thinking=True)

    lines = []
    try:
        async for m in inter.channel.history(limit=limit):
            if m.author.bot: continue
            txt = f"{m.author.display_name}: {m.content}"
            if txt.strip():
                lines.append(txt)
    except Exception as e:
        await inter.followup.send(f"履歴エラー: {e}", ephemeral=True)
        return

    if not lines:
        await inter.followup.send("メッセージがありません", ephemeral=True)
        return

    text = "\n".join(reversed(lines))
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=500
        )
        result = resp.choices[0].message.content.strip()
    except Exception as e:
        await inter.followup.send(f"要約エラー: {e}", ephemeral=True)
        return

    embed = discord.Embed(
        title="会議要約",
        description=result[:4000],
        color=0x4CAF50
    )
    embed.set_footer(text=f"{limit}件を要約")
    await inter.followup.send(embed=embed)

bot.run(TOKEN)
