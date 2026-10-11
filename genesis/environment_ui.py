"""Read-only environment observatory. All timing belongs to the model."""
from .observatory_ui import TEXT, MUTED, ACCENT


def draw_environment(app, panel):
    env = app.world.environment
    width = panel.content.w-36
    app.label("ENVIRONMENT", 18, 12, 20)
    state = "Drought" if env.drought_end is not None else env.season
    app.label(state if env.enabled else "Steady / events disabled", 18, 49, 17, ACCENT)
    app.label(f"Food multiplier: {env.multiplier:.3f}x", 18, 84, 17)
    app.label(f"Season {env.seasonal_multiplier:.3f}x / drought {env.drought_multiplier:.2f}x", 18, 116, 15, MUTED)
    next_tick = env.next_transition
    app.label(f"Next transition in {(next_tick-env.ticks)*app.world.config.timestep:.2f}s" if next_tick is not None else "No scheduled transition", 18, 148, 15)
    if env.enabled:
        cycle = env.cycle_position*app.world.config.timestep
        app.label(f"Cycle {cycle:.2f}s / {app.settings.season_length}s" if app.settings.seasons_enabled else "Seasons disabled", 18, 181, 15, MUTED)
        tick = env.drought_end or env.next_drought
        app.label(("Drought ends" if env.drought_end else "Next drought")+f" at {tick*app.world.config.timestep:.2f}s" if tick else "Droughts disabled", 18, 211, 15, MUTED)
    panel.wrap(app, "Regeneration = base rate x environment x habitat food multiplier. Only renewable food is affected. Population changes alone do not demonstrate adaptation.", 18, 248, width)
    app.label(f"EVENT HISTORY / {len(env.history)} retained / {max(0, env.total_events-len(env.history))} dropped", 18, 332, 13, ACCENT)
    rows = list(reversed(env.history))
    panel.event_offset = min(panel.event_offset, max(0, len(rows)-12))
    for i, event in enumerate(rows[panel.event_offset:panel.event_offset+12]):
        title = event.season if event.kind == "season" else event.kind.replace("_", " ").title()
        app.label(f"{event.tick*app.world.config.timestep:.2f}s / {title} / {event.multiplier:.3f}x", 18, 418+i*34, 15, (225, 183, 123) if event.kind.startswith("drought") else MUTED)
    if not rows:
        app.label("No environmental events recorded.", 18, 418, 15, MUTED)
    panel.wrap(app, "Newest first. Cyan graph markers: seasons. Gold: drought starts. Pale gold: drought ends. Markers are retained event times, not proof of causation.", 18, 851, width)
