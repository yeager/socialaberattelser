"""Sociala Berättelser — Social Stories for autism."""

import gettext
import json
import locale
import os
from datetime import datetime
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from socialaberattelser import __version__
from socialaberattelser.export import show_export_dialog

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass
for d in [Path(__file__).parent.parent / "po", Path("/usr/share/locale")]:
    if d.is_dir():
        locale.bindtextdomain("socialaberattelser", str(d))
        gettext.bindtextdomain("socialaberattelser", str(d))
        break
gettext.textdomain("socialaberattelser")
_ = gettext.gettext

APP_ID = "se.danielnylander.socialaberattelser"

TEMPLATES = [
    {
        "title": _("Going to the Dentist"),
        "steps": [
            {"text": _("Today I am going to the dentist."), "emoji": "🦷"},
            {"text": _("In the waiting room, I sit and wait for my turn."), "emoji": "🪑"},
            {"text": _("The dentist will look at my teeth."), "emoji": "👨‍⚕️"},
            {"text": _("I open my mouth wide."), "emoji": "😮"},
            {"text": _("It might feel strange but it doesn't hurt."), "emoji": "💪"},
            {"text": _("When it's done, I can be proud of myself!"), "emoji": "⭐"},
        ]
    },
    {
        "title": _("First Day of School"),
        "steps": [
            {"text": _("Today is my first day at a new school."), "emoji": "🏫"},
            {"text": _("I will meet my new teacher."), "emoji": "👩‍🏫"},
            {"text": _("There will be other children in my class."), "emoji": "👫"},
            {"text": _("I can say hello and tell them my name."), "emoji": "👋"},
            {"text": _("If I feel nervous, I can take a deep breath."), "emoji": "🫁"},
            {"text": _("It's okay to feel a little scared. It will get better!"), "emoji": "💙"},
        ]
    },
    {
        "title": _("Visiting the Supermarket"),
        "steps": [
            {"text": _("We are going to the supermarket to buy food."), "emoji": "🛒"},
            {"text": _("There might be many people and loud sounds."), "emoji": "🔊"},
            {"text": _("I can stay close to my parent."), "emoji": "👨‍👧"},
            {"text": _("I can help by holding the shopping list."), "emoji": "📝"},
            {"text": _("If it gets too noisy, I can cover my ears or use headphones."), "emoji": "🎧"},
            {"text": _("After shopping, we go home. Good job!"), "emoji": "🏠"},
        ]
    },
]


def _config_dir():
    p = Path(GLib.get_user_config_dir()) / "socialaberattelser"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _load_stories():
    path = _config_dir() / "stories.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []

def _save_stories(stories):
    (_config_dir() / "stories.json").write_text(
        json.dumps(stories, indent=2, ensure_ascii=False))


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Social Stories"))
        self.set_default_size(600, 700)
        self.stories = _load_stories()
        self.current_story = None
        self.current_step = 0

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        main_box.append(header)

        export_btn = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export (Ctrl+E)"))
        export_btn.connect("clicked", lambda *_: self._on_export())
        header.pack_end(export_btn)

        menu = Gio.Menu()
        menu.append(_("New Story"), "win.new_story")
        menu.append(_("Export Stories"), "win.export")
        menu.append(_("About Social Stories"), "app.about")
        menu.append(_("Quit"), "app.quit")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        for name, cb in [("export", self._on_export), ("new_story", self._on_new_story)]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)

        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

        # Stack: list view + story viewer
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self.list_page = self._build_list_page()
        self.stack.add_named(self.list_page, "list")

        self.viewer_page = self._build_viewer_page()
        self.stack.add_named(self.viewer_page, "viewer")

        main_box.append(self.stack)

        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("dim-label")
        self.status.set_margin_start(12)
        self.status.set_margin_bottom(4)
        main_box.append(self.status)
        GLib.timeout_add_seconds(1, self._tick)
        self._tick()

    def _tick(self):
        self.status.set_label(GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S"))
        return True

    def _on_key(self, ctrl, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK and keyval in (Gdk.KEY_e, Gdk.KEY_E):
            self._on_export()
            return True
        return False

    def _on_export(self, *_):
        all_stories = TEMPLATES + self.stories
        items = []
        for s in all_stories:
            items.append({"title": s["title"], "steps": len(s["steps"])})
        show_export_dialog(self, items, _("Social Stories"), lambda m: self.status.set_label(m))

    def _build_list_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_bottom(16)

        title = Gtk.Label(label=_("Social Stories"))
        title.add_css_class("title-2")
        box.append(title)

        subtitle = Gtk.Label(label=_("Visual stories that help prepare for new situations"))
        subtitle.add_css_class("dim-label")
        box.append(subtitle)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")

        # Built-in templates
        for tpl in TEMPLATES:
            row = Adw.ActionRow()
            row.set_title(tpl["title"])
            row.set_subtitle(_("%d steps") % len(tpl["steps"]))
            row.set_activatable(True)
            row.connect("activated", lambda r, t=tpl: self._view_story(t))
            listbox.append(row)

        # User stories
        for story in self.stories:
            row = Adw.ActionRow()
            row.set_title(story["title"])
            row.set_subtitle(_("%d steps") % len(story.get("steps", [])))
            row.set_activatable(True)
            row.connect("activated", lambda r, s=story: self._view_story(s))
            listbox.append(row)

        scroll.set_child(listbox)
        box.append(scroll)

        add_btn = Gtk.Button(label=_("Create New Story"))
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_new_story)
        box.append(add_btn)

        return box

    def _build_viewer_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_bottom(20)

        back_btn = Gtk.Button(label=_("← Back to stories"))
        back_btn.set_halign(Gtk.Align.START)
        back_btn.connect("clicked", lambda *_: self.stack.set_visible_child_name("list"))
        box.append(back_btn)

        self.story_title = Gtk.Label()
        self.story_title.add_css_class("title-2")
        box.append(self.story_title)

        self.step_emoji = Gtk.Label()
        self.step_emoji.set_css_classes(["title-1"])
        self.step_emoji.set_margin_top(20)
        box.append(self.step_emoji)

        self.step_text = Gtk.Label()
        self.step_text.add_css_class("title-3")
        self.step_text.set_wrap(True)
        self.step_text.set_max_width_chars(40)
        self.step_text.set_justify(Gtk.Justification.CENTER)
        box.append(self.step_text)

        self.step_counter = Gtk.Label()
        self.step_counter.add_css_class("dim-label")
        box.append(self.step_counter)

        nav = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        nav.set_margin_top(20)
        self.prev_btn = Gtk.Button(label=_("← Previous"))
        self.prev_btn.add_css_class("pill")
        self.prev_btn.connect("clicked", lambda *_: self._navigate(-1))
        nav.append(self.prev_btn)

        self.next_btn = Gtk.Button(label=_("Next →"))
        self.next_btn.add_css_class("suggested-action")
        self.next_btn.add_css_class("pill")
        self.next_btn.connect("clicked", lambda *_: self._navigate(1))
        nav.append(self.next_btn)
        box.append(nav)

        return box

    def _view_story(self, story):
        self.current_story = story
        self.current_step = 0
        self.story_title.set_label(story["title"])
        self._show_step()
        self.stack.set_visible_child_name("viewer")

    def _show_step(self):
        if not self.current_story:
            return
        steps = self.current_story["steps"]
        step = steps[self.current_step]
        self.step_emoji.set_label(step.get("emoji", "📖"))
        self.step_text.set_label(step["text"])
        self.step_counter.set_label(f"{self.current_step + 1} / {len(steps)}")
        self.prev_btn.set_sensitive(self.current_step > 0)
        self.next_btn.set_sensitive(self.current_step < len(steps) - 1)

    def _navigate(self, delta):
        self.current_step += delta
        self._show_step()

    def _on_new_story(self, *_):
        dialog = Adw.AlertDialog.new(_("New Story"), _("Enter a title for your story:"))
        entry = Gtk.Entry()
        entry.set_placeholder_text(_("Story title"))
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("create", _("Create"))
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_create_story, entry)
        dialog.present(self)

    def _on_create_story(self, dialog, response, entry):
        if response == "create" and entry.get_text().strip():
            story = {"title": entry.get_text().strip(), "steps": [
                {"text": _("Step 1 — edit this text"), "emoji": "📝"}
            ]}
            self.stories.append(story)
            _save_stories(self.stories)
            self.status.set_label(_("Story created: %s") % story["title"])


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.connect("activate", self._on_activate)

    def _on_activate(self, *_):
        win = self.props.active_window or MainWindow(self)
        a = Gio.SimpleAction(name="about")
        a.connect("activate", self._on_about)
        self.add_action(a)
        qa = Gio.SimpleAction(name="quit")
        qa.connect("activate", lambda *_: self.quit())
        self.add_action(qa)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        win.present()

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name=_("Social Stories"),
            application_icon=APP_ID,
            version=__version__,
            developer_name="Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://www.autismappar.se",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            comments=_("Create and view social stories for children with autism"),
        )
        dialog.present(self.props.active_window)


def main():
    app = App()
    return app.run()
