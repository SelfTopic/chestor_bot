---
title: Chat moderation
help: moderation, punishments, admin, admins
---
# 🛡 Chat moderation

The bot moderates the chat instead of separate moderator bots. The commands are for **chat
admins**, and the bot checks their rights in Telegram:

- mute, ban, kick and warns need the "**Ban users**" right;
- settings need the "**Change group info**" right;
- the admin chat is for the chat **owner** only.

The bot also needs admin rights to punish. An anonymous admin (posting as the group) can't
punish: the bot can't see who it is.

**Whom to punish:** reply to their message or put a **@username** anywhere in the text; a
numeric id goes right after the command. **Term:** `30m`, `1h`, `2 hours`, `1d`, `forever`;
no term means the default term. Everything after the term is the **reason**. Every action goes
to the admin chat, if one is linked.

### mute (/mute)

Forbid writing: `mute 30m flood`, `mute @username 1 hour spam`, `mute forever`.

- No term means the default term (30 minutes; change it with **/mute_default**).
- The term is from 30 seconds to 366 days: Telegram requires that.
- An admin can't be muted.
- When the term ends, the bot announces in the chat that the person can write again.

### unmute (/unmute)

Lift a mute early: `unmute` as a reply or `unmute @username`.

### ban (/ban)

Kick out and don't let back in: `ban 1d ads`, `ban @username forever spam`.
No term means the default term (30 minutes; change it with **/ban_default**). The bot reports
the end of a ban only to the admin chat.

### unban (/unban)

Lift a ban: the person can come back via the link.

### kick (/kick)

Kick out without a ban, they can come back via the link right away: `kick flood`.

### warn (/warn)

A warning: `warn offtopic`, `warn @username swearing`.

- Reach the **limit** (3 by default) and you get a **penalty** (a 30-minute mute by default),
  and the count resets.
- Warns **expire** after 7 days; the bot announces when a warn expires.
- All of this is configurable: **/warn_limit**, **/warn_action**, **/warn_expiry**.

### unwarn (/unwarn)

Remove the last warning. The bot says how many are left.

### warns (/warns)

The list of warnings with reasons and expiry. Anyone can see **their own**, an admin can see
**anyone's** (by reply or with a @username).

### /warn_limit

How many warns before a penalty: `/warn_limit 5`. From 1 to 20. Without a number it shows the
current one.

### /warn_action

The penalty for reaching the limit: `/warn_action mute 1h`, `/warn_action ban 1d`,
`/warn_action kick`. Without a term, mute and ban keep the previous term.

### /warn_expiry

When a warn expires: `/warn_expiry 3d`, `/warn_expiry forever`.

### /mute_default

The mute term when none is given: `/mute_default 1h`, `/mute_default forever`. Without a term
it shows the current one. Any admin can see it, changing needs the "Change group info" right.

### /ban_default

The same for bans: `/ban_default 1d`.

### /moderation_voice

How the bot talks when punishing: `/moderation_voice rough` or `/moderation_voice neutral`.

### moderation settings (/moderation)

A table menu with all chat settings and buttons: turn mute, ban, kick, warns and term end
notices on and off; scroll terms; change the warn limit and penalty; switch the voice. Any
admin can see it, changing needs the "Change group info" right. A turned-off feature answers
an admin with "turned off in the settings" and stays silent for everyone else.

### /set_admin_chat

A separate chat where the bot keeps a log: who punished whom, for what and for how long, who
changed which setting. The **owner** of both chats links them: the command in one chat, and
the bot replies with a ready command for the other.

### new welcome

The text the bot greets newcomers with: `new welcome` and up to 4,000 characters of text.

### new goodbye

The text the bot sees off those who leave with.

### new rules

The chat rules for the **rules** command.

### rules

Show the chat rules. No rules? The bot tells you how to set them.
