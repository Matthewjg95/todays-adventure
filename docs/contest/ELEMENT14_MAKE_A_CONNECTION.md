# element14 Project14 — Make a Connection

Status: **ACTIVE ENTRY TARGET**
Project: **Today's Adventure**
Submission deadline: **September 27, 2026 at 23:59 UK time**

September 18 update: see [the prepared contest package](PACKAGE.md),
[article draft](PROJECT_BLOG.md) and [current status](../STATUS.md).
The deadline is 18:59 Eastern. Physical video and current device validation
remain outstanding; the original planning checklist below is historical.

## Why Today's Adventure fits

The competition asks for an electronics project that **sends a message or signal**. Today's Adventure fits naturally without changing the project: it connects to online weather/context data, turns that data into a human-centered daily message, and communicates it through an ambient e-ink display.

The strongest framing is not "weather station." It is:

> A low-power ambient device that receives real-world signals, interprets them, and turns them into one useful or delightful message worth noticing today.

That matches the existing project identity exactly.

## Submission story

Today's Adventure should be presented as a complete signal chain:

```text
Weather / time / seasonal context
              |
              v
        Wi-Fi data fetch
              |
              v
 Context + wonder + recommendation engines
              |
              v
      Message selection
              |
              v
    M5Paper e-ink display
              |
              v
 Human receives the signal
```

The interesting engineering is the translation layer between raw data and the final message:

- fetch only what is needed
- survive network and deep-sleep failures
- explain the reliability tradeoff of repainting every normal update after field fading
- keep battery use low
- turn measurements into context rather than dumping data
- present one quiet, understandable message instead of another dashboard

## What to show in the project blog

1. **Problem / intent** — most connected displays show more data; this one tries to make the connection meaningful.
2. **Hardware** — M5Stack M5Paper v1.1, battery/power behavior, Wi-Fi connection.
3. **Signal path** — Open-Meteo/context input → scoring/recommendation/wonder logic → final e-ink message.
4. **Reliability work** — deep sleep, hardware watchdog, fetch timeouts, wake logging, battery guards, and the current repaint mitigation (unchanged-frame skipping is disabled).
5. **Display design** — scene art, headline, wonder sentence, suggestions, sun/moon context, flashcard mode.
6. **Evidence** — photos/video of the physical unit updating, examples across different weather/time conditions, desktop/demo tooling if useful.
7. **Build instructions** — setup, configuration, deployment, scene generation, and how to reproduce it.

## Scope rule

**Do not add contest-only features.** Today's Adventure already satisfies the theme. Spend effort on documentation, physical photos/video, clarity, and reproducibility instead of expanding the feature set.

## Contest positioning

The project's advantage is that the "connection" is both technical and human:

- technically, it receives networked environmental/time signals;
- computationally, it converts those signals into context;
- physically, it communicates through an ultra-low-power ambient display;
- emotionally, the output is designed to make the person notice something worthwhile about the day.

That is a stronger story than treating connectivity as an end in itself.

## Immediate checklist

- [ ] Capture clean photos of the physical M5Paper running Today's Adventure
- [ ] Record a short update/wake cycle video
- [ ] Capture several representative screens/day states
- [ ] Prepare a simple architecture/signal-flow graphic
- [ ] Turn the existing README/build notes into a step-by-step element14 project blog
- [ ] Include reliability lessons and the deep-sleep/display-controller problems solved
- [ ] Submit before September 27, 2026 23:59 UK time

## Source

Official competition: https://community.element14.com/challenges-projects/project14/p/make-a-connection
Deadline extension announcement: https://community.element14.com/challenges-projects/project14/b/news/posts/deadline-extension-make-a-connection-competition
