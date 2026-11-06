---
title: Roulette
help: roulette, bet, machine, ribbon, color, spin, casino
---
# 🎰 Roulette

Your own slot machine: a ribbon of colored cards, each color with its own payout. Bet on a color,
press «Spin» — the ribbon speeds up and stops on the card that came up. The whole game is one
message: the ribbon, the result and buttons under it.

### bet (roulette)

**bet** opens the machine. Pick a color and an amount, press «🎰 Spin» — the ribbon runs and stops
on the color that came up, and the result and your balance show up right in the message. Spin as
much as you like: the ribbon moves on from where it stopped, and your bet is remembered.

- With a bet right away: `bet red 500` — this is also how you bet an amount that has no button.
- A bet is from 100 to 100,000 CheSton, the money is taken when you press. A family member pays
  from the family account.
- Only the owner can spin. A new `bet` moves the machine down the chat, with the same ribbon and
  bet.
- The machine closes after 2 minutes without a spin — write `bet` again.
- You can play both in a group and in a private chat with the bot.

### machine screen (roulette)

From top to bottom:

- **Ribbon** — cards with payouts, the one that came up glows under the gold pointers.
- **Text** — whose machine it is, the last spin's result, your bet and balance.
- **Buttons** — colors with payouts on the left, amounts **100 · 1,000 · 5,000 · 10,000 ·
  100,000** on the right. The chosen ones are marked ✅. «🎰 Spin» at the bottom.

The «🎨 Color» and «💰 Amount» buttons above the columns explain what is where.

### colors and chances

| Color | Payout | Chance |
|:--|:--:|:--:|
| 🔴 red | ×1.8 | 28% |
| 🔵 blue | ×2.5 | 22% |
| 🟢 green | ×3 | 20% |
| 🟡 yellow | ×5 | 13% |
| ⚪ white | ×10 | 10% |

Example: you bet 1,000 on blue and blue came up — you get +2,500 on top of the bet. Another color
came up — the 1,000 is gone.

> On average the roulette returns less than you bet (white returns exactly as much): it's fun,
> not a way to earn.

### questions (roulette)

**Does it matter when I press or how the ribbon runs?** No. The color comes up the moment you
press, and the money is taken or paid right away. The ribbon only shows what came up.

**The ribbon stopped at once, without spinning — why?** The bot doesn't have this spin's video
ready yet. The result is the same, and the video will be there next time.

**I pressed a button and the bot says «not your machine».** The machine is personal: open your
own with `bet`.

**It says «the ribbon is still spinning».** While a spin is running you can't change the bet or
spin again — wait for it to stop.
