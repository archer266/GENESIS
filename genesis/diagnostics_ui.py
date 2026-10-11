"""Read-only species ledgers and explicitly timed recent rates."""
from .observatory_ui import ACCENT, MUTED


def draw_diagnostics(app, panel):
    w = app.world
    d = w.diagnostics
    row = d.snapshot(w)
    seconds, rates = d.recent(w)
    app.label("DIAGNOSTICS", 18, 12, 20)
    origin = f"Observed since legacy load at {d.since_tick*w.config.timestep:.1f}s" if d.legacy else "Lifetime totals / since experiment start"
    panel.wrap(app, origin, 18, 49, panel.content.w-36)
    app.label(f"Recent rates: last {seconds:.1f}s / per second", 18, 90, 15, MUTED)
    for index, species in enumerate(("prey", "predator")):
        y = 135+index*420
        t = d.totals[species]
        mean = row[species+'_average_energy']
        app.label(species.upper(), 18, y, 17, ACCENT if species=='prey' else (255,135,207))
        lines = [
            ("Living / average energy", f"{row[species+'_population']} / {mean:.1f}" if mean is not None else "0 / unavailable"),
            ("Births / deaths", f"{t['births']} / {sum(t['deaths_'+c] for c in ('energy','age','caught'))}"),
            ("Energy / age / caught deaths", f"{t['deaths_energy']} / {t['deaths_age']} / {t['deaths_caught']}"),
            ("Catches", str(t['catches'])),
            ("Feeding gained / overflow", f"{t['feeding_gained']:.1f} / {t['feeding_overflow']:.1f}"),
            ("Metabolism spent", f"{t['metabolism_spent']:.1f}"),
            ("Reproduction spent", f"{t['reproduction_spent']:.1f}"),
            ("Transferred to offspring", f"{t['offspring_transferred']:.1f}"),
        ]
        for i,(label,value) in enumerate(lines):
            app.label(label,18,y+34+i*29,13,MUTED)
            rendered=app.fonts[13].render(value,True,(239,246,255))
            app.screen.blit(rendered,(panel.content.w-18-rendered.get_width(),y+34+i*29))
        birth=rates[species+'_births']
        death=sum(rates[species+'_deaths_'+c] or 0 for c in ('energy','age','caught'))
        app.label(f"Recent births/deaths per s: {birth:.3f} / {death:.3f}" if birth is not None else "Recent rates: waiting for simulation time",18,y+279,13,ACCENT)
        catches=rates[species+'_catches']
        app.label(f"Recent catches/s: {catches:.3f}" if catches is not None else "Recent catches/s: unavailable",18,y+306,13,MUTED)
        if species=='predator':
            observed=t['observed_initial']+t['births']
            app.label(f"Catches / observed predator: {t['catches']/observed:.2f}" if observed else "Catches / observed predator: unavailable",18,y+334,13)
        app.label(f"Cap-blocked attempts: {t['population_cap_blocks']} / {t['predator_cap_blocks']}",18,y+361,13,MUTED)
    panel.wrap(app, "Feeding gained is energy accepted after the cap. Transfers stay within the species; reproduction spent is the extra cost. Cap blocks count eligible attempts per tick (world / predator cap), not lost births. Recent rates use up to 60 simulation seconds. Legacy totals exclude unknown earlier events. CSV retains 61 one-second snapshots plus the current row.",18,970,panel.content.w-36)
