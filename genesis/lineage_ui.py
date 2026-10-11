"""Virtualized ancestry and offspring lists within the floating Details view."""
import pygame
from .observatory_ui import TEXT, MUTED, ACCENT


class LineageView:
    VISIBLE = 5

    def __init__(self):
        self.view_id = None
        self.offsets = {"ancestors": 0, "children": 0}
        self.cache_key = None
        self.rows = {"ancestors": [], "children": []}
        self.list_rects = {}

    def view(self, oid):
        self.view_id = oid
        self.offsets = {"ancestors": 0, "children": 0}
        self.cache_key = None

    def refresh(self, app):
        archive = app.world.lineage
        key = (id(archive), archive.revision, self.view_id)
        if key != self.cache_key:
            self.rows["ancestors"] = archive.ancestry(self.view_id) if self.view_id else []
            self.rows["children"] = [(r.id, r) for r in archive.offspring(self.view_id)] if self.view_id else []
            self.cache_key = key
        for kind in self.offsets:
            self.offsets[kind] = min(self.offsets[kind], max(0, len(self.rows[kind])-self.VISIBLE))

    def scroll(self, kind, amount):
        self.offsets[kind] = max(0, min(max(0, len(self.rows[kind])-self.VISIBLE), self.offsets[kind]+amount))

    @staticmethod
    def status(record):
        return "Unavailable" if record is None else "Dead" if record.death_time is not None else "Living"

    def layout(self, app, panel, control):
        self.refresh(app)
        control("lineage_current", "View selected cell", 554)
        if app.selected_id not in app.world.organisms:
            panel.disabled.add("lineage_current")
        w = panel.content.w
        control("lineage_select", "Select living relative", 815, width=(w-42)//2)
        control("lineage_follow", "Follow relative", 815, x=w//2+3, width=(w-42)//2)
        if self.view_id not in app.world.organisms:
            panel.disabled.update(("lineage_select", "lineage_follow"))
        for kind, top in (("ancestors", 890), ("children", 1160)):
            self.list_rects[kind] = pygame.Rect(18, top, w-36, self.VISIBLE*36)
            offset = self.offsets[kind]
            rows = self.rows[kind]
            for index, (oid, record) in enumerate(rows[offset:offset+self.VISIBLE]):
                title = f"#{oid}  /  {record.species.title() if record else '?'}  /  {self.status(record)}"
                control(f"relative_{kind}_{oid}", title, top+index*36)
            control(kind+"_up", "Earlier", top+self.VISIBLE*36+7, width=95)
            control(kind+"_down", "Later", top+self.VISIBLE*36+7, x=121, width=95)
            if not offset:
                panel.disabled.add(kind+"_up")
            if offset+self.VISIBLE >= len(rows):
                panel.disabled.add(kind+"_down")

    def wheel(self, panel, point, amount):
        for kind, rect in self.list_rects.items():
            rect = rect.move(panel.content.x, panel.content.y-panel.scrolls["cell"]).clip(panel.content)
            if rect.collidepoint(point) and len(self.rows[kind]) > self.VISIBLE:
                self.scroll(kind, amount)
                return True
        return False

    def activate(self, app, panel, key):
        if key.startswith("relative_"):
            self.view(int(key.rsplit("_", 1)[1]))
            panel.scrolls["cell"] = 520
        elif key == "lineage_current":
            self.view(app.selected_id)
        elif key in ("lineage_select", "lineage_follow"):
            if self.view_id in app.world.organisms:
                app.selected_id = self.view_id
                app.follow_id = None
                if key == "lineage_follow":
                    app.toggle_follow()
        elif key in ("ancestors_up", "ancestors_down", "children_up", "children_down"):
            kind, direction = key.split("_")
            self.scroll(kind, -self.VISIBLE if direction == "up" else self.VISIBLE)

    def draw(self, app, panel):
        archive = app.world.lineage
        record = archive.records.get(self.view_id)
        w = panel.content.w
        app.label("LINEAGE EXPLORER", 18, 521, 17, ACCENT)
        if self.view_id is None:
            panel.wrap(app, "Choose a cell, then Details to explore its recorded family.", 18, 600, w-36)
        elif record is None:
            panel.wrap(app, f"#{self.view_id} / Unavailable. This record was pruned or was absent from an older save. No ancestry is inferred.", 18, 600, w-36)
        else:
            app.label(f"{record.species.title()} #{record.id} / {self.status(record)} / Gen {record.generation}", 18, 600, 17)
            if record.origin == "legacy_snapshot":
                panel.wrap(app, f"Legacy snapshot at {record.recorded_time:.2f}s. Birth details and earlier ancestry unavailable.", 18, 631, w-36)
            else:
                app.label(f"Born {record.birth_time:.2f}s / parent "+(f"#{record.parent_id}" if record.parent_id else "none (founder)"), 18, 631, 15, MUTED)
            death = f"Died {record.death_time:.2f}s / {record.death_cause}" if record.death_time is not None else "Currently living"
            app.label(death, 18, 678, 15, MUTED)
            app.label("Traits at birth" if record.origin == "birth" else "Traits at legacy observation", 18, 707, 15)
            t = record.traits
            app.label(f"Speed {t.speed:.2f} / Sense {t.sense:.2f} / Size {t.size:.2f}", 18, 734, 15)
            changes = archive.changes(record.id)
            panel.wrap(app, ("Birth change vs parent: " + " / ".join(f"{k.title()} {v:+.2f}" for k, v in changes.items()))
                       if changes else "Birth comparison unavailable: founder, missing parent or unknown birth traits.", 18, 761, w-36)
        for kind, title, top in (("ancestors", "Ancestry / this record first", 865), ("children", "Direct offspring / retained records", 1135)):
            app.label(title, 18, top, 15)
            rows = self.rows[kind]
            if not rows:
                app.label("No retained records" if kind == "children" else "No viewed record", 24, top+40, 15, MUTED)
            start = self.offsets[kind]
            app.label(f"{start+1 if rows else 0}-{min(start+self.VISIBLE, len(rows))} of {len(rows)}", 234, top+220, 13, MUTED)
        panel.wrap(app, f"Archive: {len(archive.records)} / {archive.capacity}. {archive.pruned_count} pruned; {archive.legacy_unavailable} unavailable from old saves. Living records are kept; oldest dead IDs are pruned first. Lists show retained records only. Scroll within a list or use Earlier / Later.", 18, 1408, w-36)
