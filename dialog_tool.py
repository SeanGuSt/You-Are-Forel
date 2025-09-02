import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from events.condition_helpers import condition_funcs
from events.events import event_funcs
CONDITION_KEYS = list(condition_funcs.keys())
CONDITION_KEYS.append("flag")
EVENT_KEYS = list(event_funcs.keys())

DARK_BG = "#1e1e1e"
DARK_FG = "#ffffff"
DARK_ENTRY = "#2d2d2d"

class DialogEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dialog JSON Editor")
        self.geometry("1400x700+100+50")

        self.data = {}
        self.current_npc = None
        self.current_keyword = None
        self.current_entry_index = None
        self.saving_entry = False  # Flag to prevent recursion

        self.create_widgets()
        self.apply_dark_mode()
        
        # Bind Ctrl+S for saving
        self.bind('<Control-s>', lambda e: self.save_json())

    def create_widgets(self):
        # File menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_json)
        filemenu.add_command(label="Open", command=self.load_json)
        filemenu.add_command(label="Save", command=self.save_json)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

        # Left panel: NPCs and keywords
        left_frame = tk.Frame(self, bg=DARK_BG)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # NPC list with scrollbar
        npc_frame = tk.Frame(left_frame, bg=DARK_BG)
        npc_frame.pack(fill=tk.BOTH, expand=True)
        
        npc_scrollbar = tk.Scrollbar(npc_frame, bg=DARK_ENTRY)
        npc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.npc_list = tk.Listbox(npc_frame, exportselection=False, bg=DARK_ENTRY, fg=DARK_FG,
                                   yscrollcommand=npc_scrollbar.set)
        self.npc_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.npc_list.bind("<<ListboxSelect>>", self.on_npc_select)
        npc_scrollbar.config(command=self.npc_list.yview)

        # Keyword list with scrollbar
        keyword_frame = tk.Frame(left_frame, bg=DARK_BG)
        keyword_frame.pack(fill=tk.BOTH, expand=True)
        
        keyword_scrollbar = tk.Scrollbar(keyword_frame, bg=DARK_ENTRY)
        keyword_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.keyword_list = tk.Listbox(keyword_frame, exportselection=False, bg=DARK_ENTRY, fg=DARK_FG,
                                       yscrollcommand=keyword_scrollbar.set)
        self.keyword_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.keyword_list.bind("<<ListboxSelect>>", self.on_keyword_select)
        keyword_scrollbar.config(command=self.keyword_list.yview)

        tk.Button(left_frame, text="Add NPC", command=self.add_npc).pack(fill=tk.X)
        tk.Button(left_frame, text="Add Keyword", command=self.add_keyword).pack(fill=tk.X)

        # Middle panel: entry selector
        mid_frame = tk.Frame(self, bg=DARK_BG)
        mid_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Entry list with scrollbar
        entry_frame = tk.Frame(mid_frame, bg=DARK_BG)
        entry_frame.pack(fill=tk.BOTH, expand=True)
        
        entry_scrollbar = tk.Scrollbar(entry_frame, bg=DARK_ENTRY)
        entry_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.entry_list = tk.Listbox(entry_frame, exportselection=False, bg=DARK_ENTRY, fg=DARK_FG,
                                     yscrollcommand=entry_scrollbar.set)
        self.entry_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.entry_list.bind("<<ListboxSelect>>", self.on_entry_select)
        entry_scrollbar.config(command=self.entry_list.yview)

        tk.Button(mid_frame, text="Add Entry", command=self.add_entry).pack(fill=tk.X)

        # Right panel: details
        self.detail_frame = tk.Frame(self, bg=DARK_BG)
        self.detail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Text with scrollable frame
        tk.Label(self.detail_frame, text="Text Lines:", bg=DARK_BG, fg=DARK_FG).pack(anchor="w")
        
        # Create scrollable text frame
        text_container = tk.Frame(self.detail_frame, bg=DARK_BG)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        text_canvas = tk.Canvas(text_container, bg=DARK_BG, highlightthickness=0)
        text_scrollbar = tk.Scrollbar(text_container, orient="vertical", command=text_canvas.yview, bg=DARK_ENTRY)
        self.text_frame = tk.Frame(text_canvas, bg=DARK_BG)
        
        # Configure scrolling
        self.text_frame.bind(
            "<Configure>",
            lambda e: text_canvas.configure(scrollregion=text_canvas.bbox("all"))
        )
        
        canvas_window = text_canvas.create_window((0, 0), window=self.text_frame, anchor="nw")
        text_canvas.configure(yscrollcommand=text_scrollbar.set)
        
        # Make text frame fill the canvas width
        def configure_text_frame_width(event):
            canvas_width = event.width
            text_canvas.itemconfig(canvas_window, width=canvas_width)
        
        text_canvas.bind('<Configure>', configure_text_frame_width)
        
        text_canvas.pack(side="left", fill="both", expand=True)
        text_scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            text_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        text_canvas.bind("<MouseWheel>", _on_mousewheel)



        # Conditions
        tk.Label(self.detail_frame, text="Conditions:", bg=DARK_BG, fg=DARK_FG).pack(anchor="w")
        self.conditions_frame = tk.Frame(self.detail_frame, bg=DARK_BG)
        self.conditions_frame.pack(fill=tk.X)

        self.add_condition_btn = tk.Button(self.detail_frame, text="Add Condition", command=self.add_condition_row)
        self.add_condition_btn.pack(anchor="w")

        # Events
        tk.Label(self.detail_frame, text="Events:", bg=DARK_BG, fg=DARK_FG).pack(anchor="w")
        self.events_frame = tk.Frame(self.detail_frame, bg=DARK_BG)
        self.events_frame.pack(fill=tk.X)

        self.add_event_btn = tk.Button(self.detail_frame, text="Add Event", command=self.add_event_row)
        self.add_event_btn.pack(anchor="w")

        # Save entry button
        self.save_entry_btn = tk.Button(self.detail_frame, text="Save Entry Changes", command=self.save_entry)
        self.save_entry_btn.pack(anchor="e")

    # ================= FILE OPS ================= #
    def new_json(self):
        self.data = {}
        self.refresh_npc_list()
        self.keyword_list.delete(0, tk.END)
        self.entry_list.delete(0, tk.END)
        for f in (self.text_frame, self.conditions_frame, self.events_frame):
            for w in f.winfo_children(): w.destroy()
        self.current_npc = None
        self.current_keyword = None
        self.current_entry_index = None

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.refresh_npc_list()

    def save_json(self):
        path = filedialog.asksaveasfilename(filetypes=[("JSON Files", "*.json")], defaultextension=".json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Saved", "JSON saved successfully!")

    # ================= NPC / KEYWORD ================= #
    def refresh_npc_list(self):
        self.npc_list.delete(0, tk.END)
        for npc in self.data.keys():
            self.npc_list.insert(tk.END, npc)

    def on_npc_select(self, event):
        self.save_entry()
        self.already_saved = True
        sel = self.npc_list.curselection()
        if not sel:
            return
        self.current_npc = self.npc_list.get(sel[0])
        self.keyword_list.delete(0, tk.END)
        for kw in self.data[self.current_npc].keys():
            if isinstance(self.data[self.current_npc][kw], list):
                self.keyword_list.insert(tk.END, kw)

        # Auto-select first keyword if it exists
        if self.keyword_list.size() > 0:
            self.keyword_list.selection_set(0)
            self.keyword_list.event_generate("<<ListboxSelect>>")

    def on_keyword_select(self, event):
        if not self.already_saved:
            self.save_entry()
            self.already_saved = True
        sel = self.keyword_list.curselection()
        if not sel:
            return
        self.current_keyword = self.keyword_list.get(sel[0])
        entries = self.data[self.current_npc][self.current_keyword]
        self.entry_list.delete(0, tk.END)
        for i, entry in enumerate(entries):
            preview = (entry.get("text") or ["<no text>"])[0][:30]
            self.entry_list.insert(tk.END, f"{i}: {preview}")

        # Auto-select first entry if it exists
        if self.entry_list.size() > 0:
            self.entry_list.selection_set(0)
            self.entry_list.event_generate("<<ListboxSelect>>")

    def on_entry_select(self, event):
        # Prevent recursion during save
        if not self.already_saved:
            # Auto-save current entry before switching
            self.save_entry()
        self.already_saved = False
            
        sel = self.entry_list.curselection()
        if not sel: return
        self.current_entry_index = sel[0]
        self.load_entry()

    def add_npc(self):
        name = simple_prompt("Enter new NPC key:")
        if not name:
            return
        self.save_entry()
        # Add NPC with default __hi__ and job keywords
        self.data[name] = {
            "__hi__": [
                {"text": ["Good {time_of_day}!"], "conditions": [], "events": []}
            ],
            "job": [
                {"text": ["My job is talking to you."], "conditions": [], "events": []}
            ]
        }
        self.refresh_npc_list()

        # Auto-select the new NPC
        index = list(self.data.keys()).index(name)
        self.npc_list.selection_clear(0, tk.END)
        self.npc_list.selection_set(index)
        self.npc_list.event_generate("<<ListboxSelect>>")

    def add_keyword(self):
        if not self.current_npc:
            return
        self.save_entry()
        self.already_saved = True
        name = simple_prompt("Enter new keyword:")
        if not name:
            return
        self.data[self.current_npc][name] = []
        self.on_npc_select(None)  # refresh keyword list

        # Auto-select the new keyword
        index = list(self.data[self.current_npc].keys()).index(name)
        self.keyword_list.selection_clear(0, tk.END)
        self.keyword_list.selection_set(index)
        self.keyword_list.event_generate("<<ListboxSelect>>")

    def add_entry(self):
        if not self.current_keyword:
            return
            
        # Auto-save current entry before creating new one
        self.save_entry()
        self.already_saved = True
            
        self.data[self.current_npc][self.current_keyword].append({"text": [""], "conditions": [], "events": []})
        self.on_keyword_select(None)  # refresh entry list

        # Auto-select the new entry
        index = len(self.data[self.current_npc][self.current_keyword]) - 1
        self.entry_list.selection_clear(0, tk.END)
        self.entry_list.selection_set(index)
        self.entry_list.event_generate("<<ListboxSelect>>")

    # ================= ENTRIES ================= #
    def load_entry(self):
        entry = self.data[self.current_npc][self.current_keyword][self.current_entry_index]
        # text
        for w in self.text_frame.winfo_children(): w.destroy()
        for line in entry.get("text", []):
            self.add_text_row(line)
        # conditions
        for w in self.conditions_frame.winfo_children(): w.destroy()
        for cond in entry.get("conditions", []):
            self.add_condition_row(cond)
        # events
        for w in self.events_frame.winfo_children(): w.destroy()
        for evt in entry.get("events", []):
            self.add_event_row(evt)

    def save_entry(self):
        if self.current_entry_index is None: 
            return
        try:
            entry = self.data[self.current_npc][self.current_keyword][self.current_entry_index]
        except:
            return
        lines = []
        for row in self.text_frame.winfo_children():
            chk, dd, ent = row.cond_entry[0], row.cond_entry[1], row.cond_entry[3]
            key, val = dd.get().strip(), ent.get().strip()
            cond = f"{key}={val}" if key != "flag" else val
            if cond == "=":
                cond = ""
            elif chk.var.get():
                cond = "!" + cond
            if row.event_var.get():
                dd, ent = row.main_widget[0], row.main_widget[2]  # Skip the equal sign label
                key, val = dd.get().strip(), ent.get().strip()
                main = f"{key}={val}" if key else val
            else:
                main = row.main_widget.get().strip()
            # Determine if ++ is needed
            if cond or ("=" in main):
                line = f"{cond}++{main}" if cond else f"++{main}"
            else:
                line = main
            lines.append(line)
        entry["text"] = lines
        # conditions
        entry["conditions"] = [self.format_condition_row(row) for row in self.conditions_frame.winfo_children()]
        # events
        entry["events"] = [self.format_event_row(row) for row in self.events_frame.winfo_children()]

    # ================= TEXT ================= #
    def add_text_row(self, full_line="", insert_after=None):
        frame = tk.Frame(self.text_frame, bg=DARK_BG)
        if insert_after is None:
            frame.pack(fill=tk.X, pady=1)
        else:
            # Find the position of insert_after frame and insert below it
            children = list(self.text_frame.winfo_children())
            try:
                index = children.index(insert_after)
                frame.pack(fill=tk.X, pady=1, after=insert_after)
            except ValueError:
                frame.pack(fill=tk.X, pady=1)

        # Parse full_line for condition and main
        if "++" in full_line:
            cond_part, main_part = full_line.split("++", 1)
        else:
            cond_part, main_part = "", full_line

        # Condition entry
        has_cond = "=" in cond_part
        cond_key, cond_val =  "", ""
        if has_cond:
            cond_key, cond_val = cond_part.split("=", 1)
        print(cond_key, cond_val)
        cond_entry = self._create_cond_widgets(frame, cond_key, cond_val)

        tk.Label(frame, text="++", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)

        # Determine if main_part is an event (contains '=')
        is_event = "=" in main_part

        if is_event:
            # split into key=value
            key, val = main_part.split("=", 1)
            main_widget = self._create_event_widgets(frame, key, val)
        else:
            main_widget = tk.Entry(frame, bg=DARK_ENTRY, fg=DARK_FG)
            main_widget.insert(0, main_part)
            main_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Event checkbox
        event_var = tk.BooleanVar(value=is_event)
        def toggle_event():
            # Destroy current main widget
            if isinstance(frame.main_widget, tuple):
                for w in frame.main_widget:
                    w.pack_forget()
            else:
                frame.main_widget.pack_forget()
            if event_var.get():
                # convert to dropdown + entry
                key_val_widgets = self._create_event_widgets(frame)
                frame.main_widget = key_val_widgets
            else:
                # convert back to normal entry
                new_entry = tk.Entry(frame, bg=DARK_ENTRY, fg=DARK_FG)
                new_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                frame.main_widget = new_entry

        event_chk = tk.Checkbutton(frame, text="Event", variable=event_var,
                                bg=DARK_BG, fg=DARK_FG, selectcolor=DARK_BG,
                                command=toggle_event)
        event_chk.pack(side=tk.RIGHT)

        # Add text line button
        add_btn = tk.Button(frame, text="+", width=2, 
                           command=lambda: self.add_text_row("", insert_after=frame))
        add_btn.pack(side=tk.RIGHT)

        # Remove button
        remove_btn = tk.Button(frame, text="Remove", command=frame.destroy)
        remove_btn.pack(side=tk.RIGHT)
        # Store references
        frame.cond_entry = cond_entry
        frame.event_var = event_var
        frame.main_widget = main_widget

    def _create_cond_widgets(self, parent, key="", val=""):
        negate = tk.BooleanVar(value=key.startswith("!"))
        if key.startswith("!") and len(key) > 1:
            key = key[1:]
        chk = tk.Checkbutton(parent, text="!", variable=negate, bg=DARK_BG, fg=DARK_FG, selectcolor=DARK_BG)
        chk.var = negate
        chk.pack(side=tk.LEFT)
        dd = ttk.Combobox(parent, values=CONDITION_KEYS, width=20)
        dd.set(key)
        dd.pack(side=tk.LEFT)
        equal_sign = tk.Label(parent, text="=", bg=DARK_BG, fg=DARK_FG)
        equal_sign.pack(side=tk.LEFT)
        ent = tk.Entry(parent, bg=DARK_ENTRY, fg=DARK_FG, width = 20)
        ent.insert(0, val)
        ent.pack(side=tk.LEFT)
        return (chk, dd, equal_sign, ent)
    # Helper to create event dropdown + entry
    def _create_event_widgets(self, parent, key="", val=""):
        dd = ttk.Combobox(parent, values=EVENT_KEYS, width=20)
        dd.set(key)
        dd.pack(side=tk.LEFT)
        equal_sign = tk.Label(parent, text="=", bg=DARK_BG, fg=DARK_FG)
        equal_sign.pack(side=tk.LEFT)
        ent = tk.Entry(parent, bg=DARK_ENTRY, fg=DARK_FG)
        ent.insert(0, val)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return (dd, equal_sign, ent)

    # ================= CONDITIONS ================= #
    def add_condition_row(self, cond_str=""):
        frame = tk.Frame(self.conditions_frame, bg=DARK_BG)
        frame.pack(fill=tk.X)
        negate = tk.BooleanVar(value=cond_str.startswith("!"))
        cond_str = cond_str[1:] if cond_str.startswith("!") else cond_str

        if "=" in cond_str:
            key, val = (cond_str.split("=", 1) + [""])[:2]
        else:
            key, val = ("flag", cond_str)

        chk = tk.Checkbutton(frame, text="!", variable=negate, bg=DARK_BG, fg=DARK_FG, selectcolor=DARK_BG)
        chk.pack(side=tk.LEFT)
        dd = ttk.Combobox(frame, values=CONDITION_KEYS, width=15)
        dd.set(key)
        dd.pack(side=tk.LEFT)
        tk.Label(frame, text="=", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        ent = tk.Entry(frame, bg=DARK_ENTRY, fg=DARK_FG)
        ent.insert(0, val)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn = tk.Button(frame, text="Remove", command=frame.destroy)
        btn.pack(side=tk.RIGHT)

        frame.negate, frame.dd, frame.ent = negate, dd, ent

    def format_condition_row(self, frame):
        val = frame.ent.get().strip()
        key = frame.dd.get().strip()
        if not key: return ""
        if key == "flag":
            cond = val
        else:
            cond = f"{key}={val}"
        if frame.negate.get():
            cond = "!" + cond
        return cond

    # ================= EVENTS ================= #
    def add_event_row(self, evt_str=""):
        frame = tk.Frame(self.events_frame, bg=DARK_BG)
        frame.pack(fill=tk.X)
        key, val = (evt_str.split("=", 1) + [""])[:2] if "=" in evt_str else ("", "")
        dd = ttk.Combobox(frame, values=EVENT_KEYS, width=20)
        dd.set(key)
        dd.pack(side=tk.LEFT)
        tk.Label(frame, text="=", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        ent = tk.Entry(frame, bg=DARK_ENTRY, fg=DARK_FG)
        ent.insert(0, val)
        ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn = tk.Button(frame, text="Remove", command=frame.destroy)
        btn.pack(side=tk.RIGHT)

        frame.dd, frame.ent = dd, ent

    def format_event_row(self, frame):
        val = frame.ent.get().strip()
        key = frame.dd.get().strip()
        if not key: return ""
        return f"{key}={val}"

    # ================= STYLING ================= #
    def apply_dark_mode(self):
        self.configure(bg=DARK_BG)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background=DARK_BG, foreground=DARK_FG)
        style.configure("TButton", background=DARK_ENTRY, foreground=DARK_FG)
        style.configure("TEntry", fieldbackground=DARK_ENTRY, foreground=DARK_FG)
        style.configure("TCombobox", fieldbackground=DARK_ENTRY, background=DARK_ENTRY, foreground=DARK_FG)

# Helper: quick input prompt
def simple_prompt(message):
    win = tk.Toplevel()
    win.title("Input")
    tk.Label(win, text=message).pack()
    entry = tk.Entry(win)
    entry.pack()
    entry.focus()
    result = {"value": None}
    def submit():
        result["value"] = entry.get()
        win.destroy()
    tk.Button(win, text="OK", command=submit).pack()
    def enter_as_ok(inp):
        submit()
    win.bind("<Return>", enter_as_ok)  # Bind Enter to OK
    win.wait_window()
    return result["value"]

if __name__ == "__main__":
    app = DialogEditor()
    app.mainloop()