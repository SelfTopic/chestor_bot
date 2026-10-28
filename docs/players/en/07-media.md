---
title: Videos, music and anime
help: video, videos, media, music, anime
---
# 🎬 Videos, music and anime

### video links (tiktok, youtube)

Drop a **TikTok** or **YouTube** link in any chat and the bot replies with the video itself.
No need to write anything: the link can be anywhere in the message.

- A **TikTok photo carousel** comes as one message: swipeable photos and music.
- Up to **3 links** per message.
- **Telegram limits:** bots can send videos up to 50 MB. The bot takes a long clip in lower
  quality, and if it doesn't fit at all or is longer than 15 minutes, it says the video is too
  big.
- Anything downloaded before comes **instantly**, however many times and in whatever form the
  same link is sent.

### song

**song <title>**: the bot finds up to 5 tracks and shows them as buttons: title, artist,
length. Press one and you get the audio with a cover. Example: `song unravel`.

- Tracks longer than 15 minutes don't show up.
- Anyone in the chat can press a button.
- A track downloaded before comes instantly.

### shazam

Recognize a song: reply **shazam** to a **voice message, video note, video or audio**. The bot
names the song and shows buttons to download it, like **song** does.

- The file must be up to 20 MB: Telegram won't give bots more.
- It recognizes a fragment; if it fails, try a longer and cleaner piece.
- GIFs don't work: they have no sound.

### /anime (anime)

Tokyo Ghoul episodes. They come with Russian voice-over, so the command isn't available in
your language yet. It will come later.

### 1000-7

A random Tokyo Ghoul edit from edit channels. Just write **1000-7**.

### /rich (rich, markdown)

Build a nice rich message from a Markdown file: reply **/rich** to a message with an `.md`
file. Handy for channel posts: write the text in an editor, and the bot turns it into a
message.

- Understands `#` headings, lists, tables, `>` quotes, code, links, `<details>` spoilers.
- The file must be UTF-8, up to **32,768** characters (Telegram's rich message limit).
- If Telegram rejects the markup, the bot tells you what it didn't like.
