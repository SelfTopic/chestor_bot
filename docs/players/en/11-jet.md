---
title: Jet
help: jet, crash, crash game, machine, multiplier, auto cash-out, cash out
---
# 🚀 Jet

A crash game for the whole chat. The chart climbs, the multiplier grows from x1 — and it can
crash at any moment. Cash out before the crash and you get bet × multiplier. Too late and the
bet is gone. The whole game is one message: a video, the bets and buttons under it.

### jet (/jet)

**jet** (or `/jet`) opens a machine in the chat. Then it runs round after round by itself:

1. **Bets — 9 seconds.** Tap an amount under the message and, if you like, an auto cash-out
   target.
2. **A 3-2-1 countdown.**
3. **Growth.** The multiplier grows, and a "💰 Cash out" button appears under the message.
4. **Crash.** The bot shows where it crashed and who cashed out how much, and opens bets for
   the next round right away.

Example: you bet 1,000 and cash out at x2.40 — you get 2,400, that's +1,400 on top of the bet.
Didn't make it before a crash at x1.87 — the 1,000 is gone.

- A machine lives **5 minutes**. The last round plays out, then the message turns into
  "machine closed" — type "jet" again.
- One machine per chat. While it runs, another "jet" sends a link to it.
- You can play in a group and in a private chat with the bot.

### machine screen

Top to bottom:

- **History strip** — this machine's last crashes, the newest on the left. Blue — up to x2,
  purple — up to x10, gold — higher, red — an instant crash at x1.00.
- **Video** — the countdown and the chart growing, and after a crash — where it broke off and a
  bar counting down to the next round.
- **Bets** — who bet how much and with which target, and the round's pot.
- **Text** — what's going on now, and after a crash — the results: who cashed out at what and
  whose bet was lost.

### bet

- Amounts — the left column of buttons: **100 · 1,000 · 5,000 · 10,000 · 100,000** CheSton.
- One bet per round, the amount can't be changed.
- The money is taken right away. A family member pays from the family account.
- Bets are open for 9 seconds. Too late — the bot says "bets are closed", wait for the next
  round.
- Not enough money — the bet isn't placed, you can bet less.

### auto cash-out

- Targets — the right column of buttons: **x1.5 · x2 · x3 · x5 · x10**.
- Bet first, then pick a target. While bets are open you can change it as often as you like.
- If the chart reaches the target, the bot cashes out for you at the target, even if you're not
  watching. If it crashes earlier, the bet is lost.
- With a target you can still tap "Cash out" yourself before it.
- Auto cash-out helps with a bad connection or autoplay turned off: you don't need the video
  at all.

### cash out

- During growth — the **"💰 Cash out"** button. The multiplier counts at the moment your tap
  reaches the bot.
- The result is in a popup: "Cashed out at x2.41: +2,410", "Already cashed out at x2.00" (auto
  cash-out fired) or "Too late, crashed at x1.87".
- The chart doesn't grow past **x50**: whoever held to the end gets x50 automatically.

### odds

The chart reaches multiplier m with a chance of **0.96 / m**:

| Target | Chance to get there | A 1,000 bet comes back as |
|:--|:--:|--:|
| x1.5 | 64% | 1,500 |
| x2 | 48% | 2,000 |
| x3 | 32% | 3,000 |
| x5 | 19% | 5,000 |
| x10 | 9.6% | 10,000 |
| x50 | 1.9% | 50,000 |

- About **4%** of rounds crash right away, at x1.00.
- Whatever target you pick, on average the game returns **96 of every 100** bet. A low target
  wins often but little, a high one rarely but big.
- Past crashes don't affect the next one: after three x1.00 in a row the fourth can be
  anything.

> It's fun, not a way to earn: over the long run the house is always slightly ahead.

### questions (jet)

**The video showed x2.5 but it crashed at x2.3 — why?** The video reaches your phone with a
small delay, different for everyone. The bot keeps time on its side, the same for all, and both
the crash and "Cash out" go by its clock. The exact result is always in the popup and the text.

**The videos are made in advance — so it's rigged?** The growth video is the same for every
round and always shows the same curve up to x50: there's no outcome in it. The bot picks the
crash point at random at the start of the round and shows it to no one; the odds are the same
for everyone — see the table above.

**The bot restarted mid-round — where's my money?** Bets of the unfinished round are returned,
and the machine's message says it's closed. Whoever cashed out already got paid.

**Can I bet twice in a round?** No, one bet per round. You can change the target.
