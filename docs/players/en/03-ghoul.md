---
title: Ghoul and kagune
help: ghoul, ghouls, kagune, stats, upgrade
---
# 🩸 Ghoul and kagune

### grow kagune

The main ghoul command.

- **The first time** it turns you into a ghoul with a random kagune type.
- **After that** it grows your kagune: +1 kagune strength for CheSton, **once every 10
  minutes**. If you have several kagune types, the bot asks with buttons which one to grow and
  shows the price of each.
- **The price grows** with kagune strength: the stronger it is, the more the next step costs.
- **As a dead ghoul** it's a rebirth: a new random kagune type, everything else from scratch.

Not enough money? The bot tells you how much more you need.

### race profile (/race_profile)

The ghoul profile: rank, level, kagune types and their strength, stats, hunger, health, RC
cells, how many humans and ghouls you've eaten. A dead ghoul has "dead" in every line.

### kagune (/kagune)

A guide to kagune types: where a ghoul's kakuhou is and which stat each type boosts, with a
table.

### train

Upgrade your stats for CheSton. **Works only in a private chat with the bot.**

- The bot shows a shop: each stat, its value and the price of +1, +5 and +10.
- You buy with buttons; the price grows with the current stat value.
- **Level cap:** a stat can't go above **level × 100**, health above **level × 250**. Hit the
  cap and you need a new level.

| Stat | What it does in a fight |
|:--|:--|
| 💪 Strength | damage |
| 🤸‍♂️ Dexterity | dodging |
| 🏃 Speed | who hits more often and gets an extra hit |
| ❤️ Max health | HP pool |
| ❣️ Regeneration | healing in and between fights |

### combat power (cp)

A ghoul's strength in one number, outside a fight and in a fight (with hunger and kagune).
**combat power** shows a table for each stat: the base value and what actually goes into a
fight; **cp** is the short version.

### level

Only winning fights gives XP.

- Beating someone as strong as you gives **+1%** of a level (100 wins per level).
- Beating someone k times **stronger** gives **+k%**; k times **weaker**, **+1/k%**.
- Mobs give **5 times less**.

A new level raises the stat cap and brings a reward: CheSton and RC cells, more the higher
the level. The bot tells you in a private chat.

### kagune types

Each type has its main stat that it boosts: **ukaku** is speed, **koukaku** is strength,
**rinkaku** is regeneration, **bikaku** is health. There are secondary boosts and penalties
too: the **kagune** command shows them.

Several unlocked types don't stack: a stat is boosted once, and if several types touch it, the
one for which it's the main stat wins.

### evolution / mutation

Unlocks a new kagune type or kakuja, for CheSton and RC cells at the same time.

- **A new kagune type** is always the next one on the ladder: ukaku → koukaku → rinkaku →
  bikaku. You can't pick a type or skip a step.
- **Kakuja**: stats and kagune strength ×3, but hunger drains ×4 faster. You can take it any
  time, with no level or kagune type requirements.
- **Kakuja is forever while the ghoul lives.** You can't give it back.
- **Death burns everything.** A new kagune type and kakuja don't survive rebirth: after death
  you're like a newborn ghoul.

### top snap

The top by broken fingers: `top snap` shows the first 20, `top snap 30` as many as you say,
from 1 to 50. Dead ghouls don't make the top.

### top cp

The top by combat power: `top cp` shows the first 20, `top cp 30` as many as you say, from 1
to 50. The power is the base one, the sum of stats and kagune strength as in **combat
power**, with the danger rank next to it. Hunger and other things that change power in a fight
don't affect the place. Dead ghouls don't make the top.

### top kagune

The top by kagune strength, in total or by one type, switched with buttons. The number of
places works like in **top snap**.

### death

Losing a fight **doesn't kill** you by itself. A ghoul dies if:

- **hunger reaches zero**;
- the duel winner decides to **eat** them.

After death the bot sends you an obituary in a private chat: cause of death, level, how many RC
cells you earned in that life. A dead ghoul can't do anything except **grow kagune**, which is
a rebirth.

### promo

Activate a promo code: `promo <name>`, case doesn't matter. Promo codes are posted in
[@chestor_channel](https://t.me/chestor_channel): first come, first served.

- Ghouls only.
- One promo code, one activation per player.
- A code has a number of activations and sometimes an expiry: too late and it's used up or
  expired.
