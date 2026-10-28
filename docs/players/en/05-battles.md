---
title: Fights and duels
help: fight, fights, battle, mob, mobs
---
# ⚔️ Fights and duels

### fight mob

A fight with a random enemy. **Once every 10 minutes.**

- A mob is from half as strong to twice as strong as you, based on your stats without hunger,
  so fighting a mob while hungry is more dangerous.
- **Win:** CheSton (depends on your level), XP (5 times less than for a player) and with a 15%
  chance 1–2 RC cells.
- Losing takes nothing but health.
- The bot counts your mob fights: total, wins and losses.

### duel

A fight with another player: **duel** as a reply to your opponent's message, or
**duel @username**, or **duel <id>**.

1. **Consent.** Both confirm the challenge with buttons within **a minute**, the challenger and
   the challenged. Too slow and the duel is cancelled.
2. **Handicap.** If one is **twice as strong or more**, the stronger one gets a choice in a
   private chat:
   - **⚔️ For real**: will almost surely crush them;
   - **🤝 Give a handicap**: the weaker one gets a real chance, but the favorite is still
     stronger.

   No choice within **30 seconds** means a fight with a handicap. The weaker one never learns
   about this choice.
3. **The fight** runs by itself, the log and the result come as a message.
4. **The loser's fate.** The winner chooses within **a minute**:

| Choice | What happens |
|:--|:--|
| 💰 Rob | take **10–25%** of their CheSton; from a family member, from the family account |
| 🍖 Eat | the loser's ghoul **dies**; the winner gets RC cells and restores hunger |
| 🕊️ Let go | take nothing |

No choice within a minute means the loser is **let go**. The winner gets XP either way.

**When a duel won't start:**

- one of you has no ghoul, it's dead or has less than 5 HP;
- someone is already in a fight;
- someone has never written to the bot in a private chat (the buttons go there);
- the fight limit is reached (see below);
- you can't challenge yourself or your spouse: family doesn't fight.

### fight limits

- no more than **20** duels a day per player;
- no more than **5** a day with the same opponent.

Mob fights don't count toward these limits: they have their own cooldown.

### how a fight goes

A fight lasts up to **30 rounds**. Each round the fighters hit, dodge, block and regenerate:

- **speed** decides who hits more often and whether they get an extra hit;
- **dexterity** is the chance to dodge;
- **strength** is damage, kagune makes the hit stronger;
- **regeneration** is healing right in the fight.

Whoever drops to zero HP first loses. Not decided in 30 rounds means a win on remaining
health. A draw happens too.
