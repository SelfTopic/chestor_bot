---
title: Hunger and prey
help: hunger, starving, prey, food, health, regeneration
---
# 🍖 Hunger and prey

### hunger

Shows your hunger, its tier, the time until starvation and how hunger changes your stats
right now.

- Hunger drops by itself: from 100% to zero **in a week**. As a kakuja, four times faster.
- **At zero the ghoul dies.**
- Hunger changes your stats in a fight:

| Hunger | Dexterity, speed, regeneration | Strength and kagune |
|:--|:--:|:--:|
| 75–100%: not hungry | ×1.0 | ×1.0 |
| 50–74%: slightly hungry | ×0.9 | ×1.1 |
| 25–49%: very hungry | ×0.6 | ×1.6 |
| 0–24%: starving to death | ×0.1 | ×0.5 |

> A hungry ghoul hits harder but dodges worse. At the last tier it can barely fight:
> everything drops.

### eat human

A hunt: restores **15–30%** hunger. **Once every 15 hours.**

With a **25%** chance it's an ambush: another ghoul is hunting the same prey, and a fight
starts:

- **you win**: the human is yours, plus the fight reward;
- **you lose**: the human goes to the other ghoul, hunger isn't restored;
- **draw**: while you were fighting, the human ran away.

Another way to eat is to win a duel and choose **"Eat"**.

### regen

Health, regeneration rate in HP per hour and how long until full health.

- Health recovers by itself: the higher your regeneration, the faster. Hunger affects
  regeneration too.
- **A fight needs at least 5 HP**, otherwise the bot tells you to rest.

### reminders

The bot writes to you in a private chat when:

- hunger drops to a dangerous level;
- health is fully restored;
- the ghoul dies (an obituary).

For this you need to send the bot `/start` in a private chat at least once.
