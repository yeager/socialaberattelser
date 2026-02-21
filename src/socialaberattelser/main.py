"""Sociala berättelser - Create and read social stories."""
import sys, os, json, gettext, locale
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from socialaberattelser import __version__
from socialaberattelser.accessibility import apply_large_text

TEXTDOMAIN = "socialaberattelser"
for p in [os.path.join(os.path.dirname(__file__), "locale"), "/usr/share/locale"]:
    if os.path.isdir(p):
        gettext.bindtextdomain(TEXTDOMAIN, p)
        locale.bindtextdomain(TEXTDOMAIN, p)
        break
gettext.textdomain(TEXTDOMAIN)
_ = gettext.gettext

CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), "socialaberattelser")
STORIES_FILE = os.path.join(CONFIG_DIR, "stories.json")

TEMPLATE_STORIES = [
    {"title": _("Going to School"), "steps": [
        _("I wake up in the morning."),
        _("I get dressed and eat breakfast."),
        _("I take my bag and go to school."),
        _("At school, I say hello to my teacher."),
        _("I sit at my desk and listen."),
        _("After school, I go home."),
    ]},
    {"title": _("Visiting the Doctor"), "steps": [
        _("Today I am going to the doctor."),
        _("The doctor is a nice person who helps me stay healthy."),
        _("The doctor might look in my ears and mouth."),
        _("It might feel a little strange but it is okay."),
        _("When we are done, I can go home."),
    ]},
    {"title": _("Making a Friend"), "steps": [
        _("I see someone playing alone."),
        _("I walk over and say hello."),
        _("I ask: Can I play with you?"),
        _("We play together and have fun."),
        _("Now I have a new friend!"),
    ]},
]

def _load_stories():
    try:
        with open(STORIES_FILE) as f: return json.load(f)
    except: return [dict(s) for s in TEMPLATE_STORIES]

def _save_stories(stories):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(STORIES_FILE, "w") as f: json.dump(stories, f, ensure_ascii=False, indent=2)


class StoryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="se.danielnylander.socialaberattelser",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        apply_large_text()
        win = self.props.active_window or StoryWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        for name, cb, accel in [
            ("quit", lambda *_: self.quit(), "<Control>q"),
            ("about", self._on_about, None),
            ("export", self._on_export, "<Control>e"),
        ]:
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accel: self.set_accels_for_action(f"app.{name}", [accel])

    def _on_about(self, *_):
        d = Adw.AboutDialog(application_name=_("Social Stories"), application_icon="socialaberattelser",
            version=__version__, developer_name="Daniel Nylander", website="https://www.autismappar.se",
            license_type=Gtk.License.GPL_3_0, developers=["Daniel Nylander"],
            copyright="\u00a9 2026 Daniel Nylander")
        d.present(self.props.active_window)

    def _on_export(self, *_):
        w = self.props.active_window
        if w: w.do_export()


class StoryWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, default_width=550, default_height=700, title=_("Social Stories"))
        self.stories = _load_stories()
        self.current_story = None
        self.current_step = 0
        self._build_ui()

    def _build_ui(self):
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # List view
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_header = Adw.HeaderBar(title_widget=Gtk.Label(label=_("Social Stories")))
        list_box.append(list_header)

        menu = Gio.Menu()
        menu.append(_("Export"), "app.export")
        menu.append(_("About Social Stories"), "app.about")
        menu.append(_("Quit"), "app.quit")
        list_header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))

        theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                               tooltip_text=_("Toggle dark/light theme"))
        theme_btn.connect("clicked", self._toggle_theme)
        list_header.pack_end(theme_btn)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.story_list = Gtk.ListBox()
        self.story_list.add_css_class("boxed-list")
        self.story_list.set_margin_start(16)
        self.story_list.set_margin_end(16)
        self.story_list.set_margin_top(12)
        scroll.set_child(self.story_list)
        list_box.append(scroll)

        add_btn = Gtk.Button(label=_("New Story"))
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.set_halign(Gtk.Align.CENTER)
        add_btn.set_margin_top(8)
        add_btn.set_margin_bottom(8)
        add_btn.connect("clicked", self._on_new_story)
        list_box.append(add_btn)

        self.stack.add_named(list_box, "list")

        # Read view
        read_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        read_header = Adw.HeaderBar()
        back_btn = Gtk.Button(icon_name="go-previous-symbolic")
        back_btn.connect("clicked", lambda *_: self.stack.set_visible_child_name("list"))
        read_header.pack_start(back_btn)
        read_box.append(read_header)

        self.step_title = Gtk.Label(label="")
        self.step_title.add_css_class("title-2")
        self.step_title.set_margin_top(24)
        read_box.append(self.step_title)

        self.step_label = Gtk.Label(label="", wrap=True)
        self.step_label.add_css_class("title-3")
        self.step_label.set_margin_top(32)
        self.step_label.set_margin_start(24)
        self.step_label.set_margin_end(24)
        self.step_label.set_vexpand(True)
        read_box.append(self.step_label)

        self.step_counter = Gtk.Label(label="")
        self.step_counter.add_css_class("dim-label")
        self.step_counter.set_margin_top(8)
        read_box.append(self.step_counter)

        nav_box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        nav_box.set_margin_top(8)
        nav_box.set_margin_bottom(16)
        self.prev_btn = Gtk.Button(label=_("Previous"))
        self.prev_btn.add_css_class("pill")
        self.prev_btn.connect("clicked", self._prev_step)
        nav_box.append(self.prev_btn)
        self.next_btn = Gtk.Button(label=_("Next"))
        self.next_btn.add_css_class("suggested-action")
        self.next_btn.add_css_class("pill")
        self.next_btn.connect("clicked", self._next_step)
        nav_box.append(self.next_btn)
        read_box.append(nav_box)

        self.stack.add_named(read_box, "read")
        self.set_content(self.stack)
        self._refresh_list()

    def _refresh_list(self):
        while (child := self.story_list.get_first_child()):
            self.story_list.remove(child)
        for i, story in enumerate(self.stories):
            row = Adw.ActionRow(title=story["title"],
                                 subtitle=_("%d steps") % len(story["steps"]))
            row.set_activatable(True)
            row.connect("activated", self._on_read_story, i)
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            self.story_list.append(row)

    def _on_read_story(self, row, idx):
        self.current_story = idx
        self.current_step = 0
        self._show_step()
        self.stack.set_visible_child_name("read")

    def _show_step(self):
        story = self.stories[self.current_story]
        self.step_title.set_label(story["title"])
        self.step_label.set_label(story["steps"][self.current_step])
        self.step_counter.set_label(_("Step %d of %d") % (self.current_step + 1, len(story["steps"])))
        self.prev_btn.set_sensitive(self.current_step > 0)
        self.next_btn.set_sensitive(self.current_step < len(story["steps"]) - 1)

    def _prev_step(self, *_):
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def _next_step(self, *_):
        story = self.stories[self.current_story]
        if self.current_step < len(story["steps"]) - 1:
            self.current_step += 1
            self._show_step()

    def _on_new_story(self, *_):
        d = Adw.MessageDialog(transient_for=self, heading=_("New Story"), body=_("Enter story title:"))
        entry = Gtk.Entry(placeholder_text=_("e.g. Going to the Store"))
        d.set_extra_child(entry)
        d.add_response("cancel", _("Cancel"))
        d.add_response("add", _("Add"))
        d.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        def on_resp(dlg, resp):
            if resp == "add" and entry.get_text().strip():
                self.stories.append({"title": entry.get_text().strip(),
                                      "steps": [_("First step...")]})
                _save_stories(self.stories)
                self._refresh_list()
        d.connect("response", on_resp)
        d.present()

    def do_export(self):
        from socialaberattelser.export import export_csv, export_json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        ts = GLib.DateTime.new_now_local().format("%Y%m%d_%H%M%S")
        data = [{"date": "", "details": s["title"], "result": f'{len(s["steps"])} steps'} for s in self.stories]
        export_csv(data, os.path.join(CONFIG_DIR, f"export_{ts}.csv"))
        export_json(data, os.path.join(CONFIG_DIR, f"export_{ts}.json"))

    def _toggle_theme(self, *_):
        mgr = Adw.StyleManager.get_default()
        mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if mgr.get_dark() else Adw.ColorScheme.FORCE_DARK)


def main():
    app = StoryApp()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
