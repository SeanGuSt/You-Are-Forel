import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from events.condition_helpers import condition_funcs
from events.events import event_funcs
from tkinter import font
CONDITION_KEYS = list(condition_funcs.keys())
CONDITION_KEYS.append("flag")
CONDITION_KEYS.sort()
EVENT_KEYS = list(event_funcs.keys())
EVENT_KEYS.sort()

# Add trigger options for events
TRIGGER_OPTIONS = ["on_step", "after_step"]

DARK_BG = "#1e1e1e"
DARK_FG = "#ffffff"
DARK_ENTRY = "#2d2d2d"
class CollapsibleSection(tk.Frame):
    def __init__(self, parent, title, *args, **kwargs):
        super().__init__(parent, bg=DARK_BG, *args, **kwargs)

        self.header = tk.Button(
            self, text="▼ " + title, anchor="w",
            bg=DARK_BG, fg=DARK_FG, relief="flat",
            command=self.toggle
        )
        self.header.pack(fill=tk.X)

        self.container = tk.Frame(self, bg=DARK_BG)
        self.container.pack(fill=tk.X)

        self.collapsed = False
        self.title = title

    def toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.container.forget()
            self.header.config(text="► " + self.title)
        else:
            self.container.pack(fill=tk.X)
            self.header.config(text="▼ " + self.title)

class DialogEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dialog/Event JSON Editor")
        self.geometry("1400x700+100+50")

        self.data = {}
        self.current_npc = None
        self.current_keyword = None
        self.current_entry_index = None
        self.saving_entry = False  # Flag to prevent recursion
        self.is_event_mode = False  # Track if we're editing events
        self.all_flags, self.all_quests = scan_flags_and_quests()
        self.textbox_width = calculate_text_widget_width()

        self.create_widgets()
        self.apply_dark_mode()
        
        self.bind('<Control-s>', lambda e: self.save_json())
        self.bind('<Control-d>', lambda e: self.new_dialog_json())
        self.bind('<Control-e>', lambda e: self.new_event_json())
        self.bind('<Alt-s>', lambda e: self.save_entry())
        self.bind('<Control-o>', lambda e: self.load_json())
        self.bind('<Escape>', lambda e: self.destroy())

    def create_widgets(self):
        # File menu
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Dialog (Ctrl+D)", command=self.new_dialog_json)
        filemenu.add_command(label="New Event (Ctrl+E)", command=self.new_event_json)
        filemenu.add_command(label="Open (Ctrl+O)", command=self.load_json)
        filemenu.add_command(label="Save (Ctrl+S)", command=self.save_json)
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
        
        npc_btn_frame = tk.Frame(left_frame)
        npc_btn_frame.pack()
        self.add_npc_btn = tk.Button(npc_btn_frame, text="Add NPC", command=self.add_npc)
        self.delete_npc_btn = tk.Button(npc_btn_frame, text="Delete NPC", command=self.delete_npc)
        self.add_npc_btn.pack(side=tk.LEFT, fill=tk.X)
        self.delete_npc_btn.pack(side=tk.RIGHT, fill=tk.X)
        
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
        
        keyword_btn_frame = tk.Frame(left_frame)
        keyword_btn_frame.pack()
        self.add_keyword_btn = tk.Button(keyword_btn_frame, text="Add Term", command=self.add_keyword)
        self.delete_keyword_btn = tk.Button(keyword_btn_frame, text="Delete Term", command=self.delete_keyword)
        self.add_keyword_btn.pack(side=tk.LEFT, fill=tk.X)
        self.delete_keyword_btn.pack(side=tk.RIGHT, fill=tk.X)

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

        self.add_entry_btn = tk.Button(mid_frame, text="Add Entry", command=self.add_entry)
        self.add_entry_btn.pack(fill=tk.X)

        # Right panel: details
        self.detail_frame = tk.Frame(self, bg=DARK_BG)
        self.detail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Text with scrollable frame
        tk.Label(self.detail_frame, text="Text Lines:", bg=DARK_BG, fg=DARK_FG).pack(anchor="w")
        
        # Create scrollable text frame
        text_container = tk.Frame(self.detail_frame, bg=DARK_BG)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.text_canvas = tk.Canvas(text_container, bg=DARK_BG, highlightthickness=0)
        text_scrollbar = tk.Scrollbar(text_container, orient="vertical", command=self.text_canvas.yview, bg=DARK_ENTRY)
        self.text_frame = tk.Frame(self.text_canvas, bg=DARK_BG)
        
        # Configure scrolling
        self.text_frame.bind(
            "<Configure>",
            lambda e: self.text_canvas.configure(scrollregion=self.text_canvas.bbox("all"))
        )
        
        canvas_window = self.text_canvas.create_window((0, 0), window=self.text_frame, anchor="nw")
        self.text_canvas.configure(yscrollcommand=text_scrollbar.set)
        
        # Make text frame fill the canvas width
        def configure_text_frame_width(event):
            canvas_width = event.width
            self.text_canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.text_canvas.bind('<Configure>', configure_text_frame_width)
        
        self.text_canvas.pack(side="left", fill="both", expand=True)
        text_scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.text_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.text_canvas.bind("<MouseWheel>", _on_mousewheel)

        # Conditions
        self.conditions_section = CollapsibleSection(self.detail_frame, "Conditions")
        self.conditions_section.pack(fill=tk.X)

        self.conditions_frame = tk.Frame(self.conditions_section.container, bg=DARK_BG)
        self.conditions_frame.pack(fill=tk.X)

        self.add_condition_btn = tk.Button(
            self.conditions_section.container, text="Add Condition",
            command=self.add_condition_row
        )
        self.add_condition_btn.pack(anchor="w")

        # Events/Trigger section (changes based on mode)
        self.events_section = CollapsibleSection(self.detail_frame, "Events")
        self.events_section.pack(fill=tk.X)

        self.events_frame = tk.Frame(self.events_section.container, bg=DARK_BG)
        self.events_frame.pack(fill=tk.X)

        self.add_event_btn = tk.Button(
            self.events_section.container, text="Add Event",
            command=self.add_event_row
        )
        self.add_event_btn.pack(anchor="w")

        # Aliases (only for dialog mode)
        self.aliases_section = CollapsibleSection(self.detail_frame, "Keyword Aliases")
        self.aliases_section.pack(fill=tk.X)

        self.aliases_frame = tk.Frame(self.aliases_section.container, bg=DARK_BG)
        self.aliases_frame.pack(fill=tk.X)

        self.add_alias_btn = tk.Button(
            self.aliases_section.container, text="Add Alias",
            command=self.add_alias_mapping_row
        )
        self.add_alias_btn.pack(anchor="w")

    def update_ui_for_mode(self):
        """Update UI elements based on current mode (dialog vs event)"""
        if self.is_event_mode:
            # Update labels and sections for event mode
            self.events_section.header.config(text="▼ Trigger" if not self.events_section.collapsed else "► Trigger")
            self.events_section.title = "Trigger"
            self.add_event_btn.config(text="Set Trigger")
            
            # Hide aliases section in event mode
            self.aliases_section.pack_forget()
            
            # Update button text
            self.add_keyword_btn.config(text="Add Event")
        else:
            # Update labels and sections for dialog mode
            self.events_section.header.config(text="▼ Events" if not self.events_section.collapsed else "► Events")
            self.events_section.title = "Events"
            self.add_event_btn.config(text="Add Event")
            
            # Show aliases section in dialog mode
            self.aliases_section.pack(fill=tk.X)
            
            # Update button text
            self.add_keyword_btn.config(text="Add Keyword")

    def create_value_field(self, parent, field_type="", initial=""):
        """
        Creates a smart value widget that updates based on field_type.
        - field_type: the selected key (flag, quest, have_quest_step, give_quest_hint, etc.)
        - initial: initial text
        Returns: a (container_frame, get_value_fn) tuple
        """
        container = tk.Frame(parent, bg=DARK_BG)
        container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        var = tk.StringVar(value=initial)

        def rebuild(new_type=None):
            nonlocal field_type
            if new_type:
                field_type = new_type
            for w in container.winfo_children():
                w.destroy()

            # ========== FLAG ==========
            if "flag" in field_type:
                box = ttk.Combobox(container, values=self.all_flags, textvariable=var, width=40)
                box.pack(side=tk.LEFT, fill=tk.X)

            # ========== QUEST STEP / HINT ==========
            elif "quest_step" in field_type or "quest_hint" in field_type:
                init_split = initial.split("__")
                quest_box = ttk.Combobox(container, values=list(self.all_quests.keys()), width=30)
                quest_box.pack(side=tk.LEFT)
                quest_box.set(init_split[0])
                if len(init_split) == 2:
                    if "step" in field_type:
                        part_box = ttk.Combobox(container, values=self.all_quests[init_split[0]]["steps"], width=30)
                    elif "hint" in field_type:
                        part_box = ttk.Combobox(container, values=self.all_quests[init_split[0]]["hints"], width=30)
                    part_box.set(init_split[1])
                else:
                    part_box = ttk.Combobox(container, width=25)
                 
                part_box.pack(side=tk.LEFT)

                def update_parts(*a):
                    qid = quest_box.get()
                    if not qid: return
                    parts = self.all_quests.get(qid, {}).get(
                        "steps" if "quest_step" in field_type else "hints", []
                    )
                    part_box.set("")
                    part_box["values"] = parts

                quest_box.bind("<<ComboboxSelected>>", update_parts)

                def update_val(*a):
                    if quest_box.get() and part_box.get():
                        var.set(f"{quest_box.get()}__{part_box.get()}")
                        
                part_box.bind("<<ComboboxSelected>>", update_val)

            # ========== QUEST (like mid_quest, give_quest, etc.) ==========
            elif "quest" in field_type:
                box = ttk.Combobox(container, values=list(self.all_quests.keys()), textvariable=var, width=25)
                box.pack(side=tk.LEFT, fill=tk.X)
            elif "text" == field_type:
                ent = tk.Text(container, bg=DARK_ENTRY, fg=DARK_FG, height = 4, width=self.textbox_width, wrap = tk.WORD)
                ent.insert('1.0', var.get())
                def update_var(*args):
                    var.set(ent.get('1.0', tk.END).strip())

                ent.bind('<KeyRelease>', update_var)
                ent.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # ========== DEFAULT ==========
            else:
                ent = tk.Entry(container, textvariable=var, bg=DARK_ENTRY, fg=DARK_FG, width=25)
                ent.pack(side=tk.LEFT, fill=tk.X)

        rebuild()

        return container, (lambda: var.get()), rebuild

    # ================= FILE OPS ================= #
    def new_dialog_json(self):
        self.data = {}
        self.is_event_mode = False
        self.refresh_npc_list()
        self.keyword_list.delete(0, tk.END)
        self.entry_list.delete(0, tk.END)
        for f in (self.text_frame, self.conditions_frame, self.events_frame):
            for w in f.winfo_children(): w.destroy()
        self.current_npc = None
        self.current_keyword = None
        self.current_entry_index = None
        self.update_ui_for_mode()

    def new_event_json(self):
        self.data = {"event": {}}
        self.is_event_mode = True
        self.refresh_npc_list()
        self.keyword_list.delete(0, tk.END)
        self.entry_list.delete(0, tk.END)
        for f in (self.text_frame, self.conditions_frame, self.events_frame):
            for w in f.winfo_children(): w.destroy()
        self.current_npc = "event"
        self.current_keyword = None
        self.current_entry_index = None
        self.update_ui_for_mode()
        # Auto-select the event "NPC"
        self.npc_list.selection_set(0)
        self.npc_list.event_generate("<<ListboxSelect>>")

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        # Detect if this is an event file
        self.is_event_mode = path.endswith("event.json")
        if self.is_event_mode:
            self.data = {"event":self.data}
        self.update_ui_for_mode()
        self.refresh_npc_list()

    def save_json(self):
        path = filedialog.asksaveasfilename(filetypes=[("JSON Files", "*.json")], defaultextension=".json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            if self.current_npc == "event":
                json.dump(self.data["event"], f, indent=2, ensure_ascii=False)
            else:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Saved", "JSON saved successfully!")

    # ================= NPC / KEYWORD ================= #
    def refresh_npc_list(self):
        self.npc_list.delete(0, tk.END)
        for npc in self.data.keys():
            self.npc_list.insert(tk.END, npc)
        # Auto-select first entry if it exists
        if self.npc_list.size() > 0:
            self.npc_list.selection_set(0)
            self.npc_list.event_generate("<<ListboxSelect>>")

    def on_npc_select(self, event):
        self.save_entry()
        self.already_saved = True
        sel = self.npc_list.curselection()
        if not sel:
            return
        self.current_npc = self.npc_list.get(sel[0])
        self.keyword_list.delete(0, tk.END)
        
        if self.is_event_mode:
            # In event mode, keywords are event names
            for kw in self.data[self.current_npc].keys():
                if isinstance(self.data[self.current_npc][kw], dict):
                    self.keyword_list.insert(tk.END, kw)
        else:
            # In dialog mode, keywords are conversation topics
            for kw in self.data[self.current_npc].keys():
                if isinstance(self.data[self.current_npc][kw], list):
                    self.keyword_list.insert(tk.END, kw)

        # Auto-select first keyword if it exists
        if self.keyword_list.size() > 0:
            self.keyword_list.selection_set(0)
            self.keyword_list.event_generate("<<ListboxSelect>>")
        
        # Initialize aliases only for dialog mode
        if not self.is_event_mode:
            if "aliases" not in self.data[self.current_npc]:
                self.data[self.current_npc]["aliases"] = {}
            if "contextual_aliases" not in self.data[self.current_npc]:
                self.data[self.current_npc]["contextual_aliases"] = {}

    def on_keyword_select(self, event):
        if not self.already_saved:
            self.save_entry()
            self.already_saved = True
        sel = self.keyword_list.curselection()
        if not sel:
            return
        self.current_keyword = self.keyword_list.get(sel[0])
        
        self.entry_list.delete(0, tk.END)
        
        if self.is_event_mode:
            # In event mode, there's only one "entry" per event
            event_data = self.data[self.current_npc][self.current_keyword]
            preview = (event_data.get("script") or ["<no text>"])[0][:30]
            self.entry_list.insert(tk.END, f"0: {preview}")
        else:
            # In dialog mode, there can be multiple entries
            entries = self.data[self.current_npc][self.current_keyword]
            for i, entry in enumerate(entries):
                preview = (entry.get("script") or ["<no text>"])[0][:30]
                self.entry_list.insert(tk.END, f"{i}: {preview}")

        # Handle aliases only in dialog mode
        if not self.is_event_mode:
            for w in self.aliases_frame.winfo_children(): 
                w.destroy()

            aliases = self.data[self.current_npc].get("aliases", {})
            contextual = self.data[self.current_npc].get("contextual_aliases", {})

            # Load general aliases pointing to this keyword
            for alias, target in aliases.items():
                if target == self.current_keyword:
                    self.add_alias_mapping_row(alias, "")

            # Load contextual aliases pointing to this keyword
            for ctx_kw, mapping in contextual.items():
                for alias, target in mapping.items():
                    if target == self.current_keyword:
                        self.add_alias_mapping_row(alias, ctx_kw)

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
        self.text_canvas.yview_moveto(0.0)

    def add_npc(self):
        # Check if we should prevent adding regular NPCs when in event mode
        if self.is_event_mode:
            messagebox.showwarning("Cannot Add NPC", "Cannot add regular NPCs in event mode. Use 'New Dialog' to create a dialog file.")
            return
            
        # Check if we should prevent adding "event" when other NPCs exist
        if len(self.data) > 0 and not self.is_event_mode:
            name = simple_prompt("Enter new NPC key:")
            if name == "event":
                messagebox.showwarning("Cannot Add Event", "Cannot add 'event' NPC when other NPCs exist. Use 'New Event' to create an event file.")
                return
        else:
            name = simple_prompt("Enter new NPC key:")
            
        if not name:
            return
        self.save_entry()
        
        if name == "event":
            # Switch to event mode
            self.data = {"event": {}}
            self.is_event_mode = True
            self.update_ui_for_mode()
        else:
            # Add NPC with default __hi__ and job keywords
            self.data[name] = {
                "__hi__": [
                    {"script": ["Good {time_of_day}!"], "conditions": [], "events": []}
                ],
                "job": [
                    {"script": ["My job is talking to you."], "conditions": [], "events": []}
                ]
            }
        
        self.refresh_npc_list()

        # Auto-select the new NPC
        index = list(self.data.keys()).index(name)
        self.npc_list.selection_clear(0, tk.END)
        self.npc_list.selection_set(index)
        self.npc_list.event_generate("<<ListboxSelect>>")

    def delete_npc(self):
        if not self.current_npc or self.is_event_mode:
            return
        if self.current_npc in self.data and len(self.data.keys()) > 1:
            if messagebox.askyesno("Delete NPC", f"Delete NPC '{self.current_npc}'?"):
                # Auto-select the prior npc (or the first one, if there is no "prior")
                index = list(self.data.keys()).index(self.current_keyword) - 1
                if index < 0:
                    index = 0
                self.data.pop(self.current_npc)
                self.npc_list.selection_clear(0, tk.END)
                self.npc_list.selection_set(index)
                self.npc_list.event_generate("<<ListboxSelect>>")
        

    def add_keyword(self):
        if not self.current_npc:
            return
        self.save_entry()
        self.already_saved = True
        
        if self.is_event_mode:
            name = simple_prompt("Enter new event name:")
        else:
            name = simple_prompt("Enter new keyword:")
            
        if not name:
            return
            
        if self.is_event_mode:
            # Create event structure
            self.data[self.current_npc][name] = {
                "script": [""],
                "conditions": [],
                "trigger": "on_step"  # Default trigger
            }
        else:
            # Create keyword structure
            self.data[self.current_npc][name] = [
                {
                    "script" : [""],
                    "conditions" : [],
                    "events" : []
                }
            ]
            
        self.on_npc_select(None)  # refresh keyword list

        # Auto-select the new keyword
        keywords = [k for k in self.data[self.current_npc].keys() 
                   if (isinstance(self.data[self.current_npc][k], dict) if self.is_event_mode 
                       else isinstance(self.data[self.current_npc][k], list))]
        index = keywords.index(name)
        self.keyword_list.selection_clear(0, tk.END)
        self.keyword_list.selection_set(index)
        self.keyword_list.event_generate("<<ListboxSelect>>")

    def delete_keyword(self):
        if not self.current_npc or not self.current_keyword:
            return
        if self.current_keyword in self.data[self.current_npc] and len(self.data[self.current_npc].keys()) > 1:
            if messagebox.askyesno("Delete Term", f"Delete term '{self.current_keyword}'?"):
                # Auto-select the prior keyword (or the first, if there is no "prior")
                index = list(self.data[self.current_npc].keys()).index(self.current_keyword) - 1
                self.data[self.current_npc].pop(self.current_keyword)
                self.on_npc_select(None)  # refresh keyword list
                self.keyword_list.selection_clear(0, tk.END)
                self.keyword_list.selection_set(index)
                self.keyword_list.event_generate("<<ListboxSelect>>")
        

    def add_entry(self):
        if not self.current_keyword:
            return
        
        if self.is_event_mode:
            # Events don't have multiple entries
            messagebox.showinfo("Info", "Events can only have one entry. Edit the existing entry.")
            return
            
        # Auto-save current entry before creating new one
        self.save_entry()
        self.already_saved = True
            
        self.data[self.current_npc][self.current_keyword].append({"script": [""], "conditions": [], "events": []})
        self.on_keyword_select(None)  # refresh entry list

        # Auto-select the new entry
        index = len(self.data[self.current_npc][self.current_keyword]) - 1
        self.entry_list.selection_clear(0, tk.END)
        self.entry_list.selection_set(index)
        self.entry_list.event_generate("<<ListboxSelect>>")

    # ================= ENTRIES ================= #
    def load_entry(self):
        if self.is_event_mode:
            entry = self.data[self.current_npc][self.current_keyword]
        else:
            entry = self.data[self.current_npc][self.current_keyword][self.current_entry_index]
            
        # text
        for w in self.text_frame.winfo_children(): w.destroy()
        for line in entry.get("script", []):
            if "force_end=" in entry.get("events" if not self.is_event_mode else "trigger", []) and not line:
                continue
            self.add_text_row(line)
        # conditions
        for w in self.conditions_frame.winfo_children(): w.destroy()
        for cond in entry.get("conditions", []):
            self.add_condition_row(cond)
        # events/trigger
        for w in self.events_frame.winfo_children(): w.destroy()
        if self.is_event_mode:
            # For events, add trigger instead of events
            trigger = entry.get("trigger", "on_step")
            self.add_trigger_row(trigger)
        else:
            # For dialog, add events
            for evt in entry.get("events", []):
                self.add_event_row(evt)

    def save_entry(self):
        if self.current_entry_index is None: 
            return
        try:
            if self.is_event_mode:
                entry = self.data[self.current_npc][self.current_keyword]
            else:
                entry = self.data[self.current_npc][self.current_keyword][self.current_entry_index]
        except:
            return
        lines = []
        for row in self.text_frame.pack_slaves():
            chk, dd, ent = row.cond_entry[0], row.cond_entry[1], row.cond_entry[3]
            key, val = dd.get().strip(), ent.get_val().strip()
            cond = f"{key}={val}" if key != "flag" else val
            if "flag" in key and val not in self.all_flags:
                self.all_flags.append(val)
            if cond == "=":
                cond = ""#If condition is empty, ignore it.
            elif chk.var.get():
                cond = "!" + cond#If it's negated, negate it
            dd, ent = row.main_widget[0], row.main_widget[2]  # Skip the equal sign label
            key, val = dd.get().strip(), ent.get_val().strip()
            main = f"{key}={val}" if key and key != "text" else val
            # Determine if ++ is needed
            if cond:
                line = f"{cond}++{main}"
            else:
                line = main
            lines.append(line)
        entry["script"] = lines
        # conditions
        entry["conditions"] = [self.format_condition_row(row) for row in self.conditions_frame.winfo_children()]
        
        # events/trigger
        if self.is_event_mode:
            # For events, save trigger (should only be one)
            trigger_rows = list(self.events_frame.winfo_children())
            if trigger_rows:
                entry["trigger"] = self.format_trigger_row(trigger_rows[0])
            else:
                entry["trigger"] = "on_step"  # default
        else:
            # For dialog, save events
            entry["events"] = [self.format_event_row(row) for row in self.events_frame.winfo_children()]
            
        if not self.is_event_mode and "force_end=" in entry["events"]:
            lines.append("")
            
        # Handle aliases only for dialog mode
        if not self.is_event_mode:
            aliases = self.data[self.current_npc].setdefault("aliases", {})
            contextual = self.data[self.current_npc].setdefault("contextual_aliases", {})

            # Remove old entries pointing to this keyword
            for k, v in list(aliases.items()):
                if v == self.current_keyword:
                    del aliases[k]
            for ctx, amap in list(contextual.items()):
                for a, tgt in list(amap.items()):
                    if tgt == self.current_keyword:
                        del amap[a]
                if not amap:
                    del contextual[ctx]

            # Add current rows
            for row in self.aliases_frame.winfo_children():
                alias = row.alias_ent.get().strip()
                ctx = row.ctx_dd.get().strip()
                if alias:
                    if ctx:
                        contextual.setdefault(ctx, {})[alias] = self.current_keyword
                    else:
                        aliases[alias] = self.current_keyword

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
        elif cond_part:
            cond_key, cond_val = "flag", cond_part
        # Condition entry
        cond_chk, cond_dd, cond_eq, cond_val_frame = self._create_cond_widgets(frame, cond_key, cond_val)
        # Wrap with get_val
        frame.cond_entry = (cond_chk, cond_dd, cond_eq, cond_val_frame)
        frame.get_cond_val = lambda: cond_val_frame.get_val() if hasattr(cond_val_frame, "get_val") else cond_val_frame.get()

        tk.Label(frame, text="++", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)

        # Determine if main_part is an event (contains '=')
        is_event = "=" in main_part

        # Event/main part
        if is_event:
            key, val = main_part.split("=", 1) 
        else:
            key, val = "text", main_part
        main_dd, main_eq, main_val_frame = self._create_event_widgets(frame, key, val)
        frame.main_widget = (main_dd, main_eq, main_val_frame)
        frame.get_main_val = lambda: main_val_frame.get_val() if hasattr(main_val_frame, "get_val") else main_val_frame.get()

        # Add text line button
        add_btn = tk.Button(frame, text="+", width=2, 
                           command=lambda: self.add_text_row("", insert_after=frame))
        add_btn.pack(side=tk.RIGHT, padx=1)

        # Remove button
        remove_btn = tk.Button(frame, text="-", width=2, command=frame.destroy)
        remove_btn.pack(side=tk.RIGHT, padx=1)

    def _create_event_widgets(self, parent, key="", val=""):
        dd = ttk.Combobox(parent, values=EVENT_KEYS, width=20)
        dd.set(key)
        dd.pack(side=tk.LEFT)

        eq = tk.Label(parent, text="=", bg=DARK_BG, fg=DARK_FG)
        eq.pack(side=tk.LEFT)

        field_frame, get_val, rebuild = self.create_value_field(parent, key, val)
        field_frame.get_val = get_val

        dd.bind("<<ComboboxSelected>>", lambda e: rebuild(dd.get()))

        # Just return (dd, eq, field_frame) like before
        return (dd, eq, field_frame)
        
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

        eq = tk.Label(parent, text="=", bg=DARK_BG, fg=DARK_FG)
        eq.pack(side=tk.LEFT)

        field_frame, get_val, rebuild = self.create_value_field(parent, key, val)
        field_frame.get_val = get_val
        dd.bind("<<ComboboxSelected>>", lambda e: rebuild(dd.get()))

        return (chk, dd, eq, field_frame)

    # ================= CONDITIONS ================= #
    def add_condition_row(self, cond_str=""):
        frame = tk.Frame(self.conditions_frame, bg=DARK_BG)
        frame.pack(fill=tk.X)

        # Parse initial string into key/val
        negate = tk.BooleanVar(value=cond_str.startswith("!"))
        cond_str = cond_str[1:] if cond_str.startswith("!") else cond_str

        if not cond_str:
            key, val = "", ""
        elif "=" in cond_str:
            key, val = (cond_str.split("=", 1) + [""])[:2]
        else:
            key, val = ("flag", cond_str)

        # Negate checkbox
        chk = tk.Checkbutton(frame, text="!", variable=negate, bg=DARK_BG, fg=DARK_FG, selectcolor=DARK_BG)
        chk.pack(side=tk.LEFT)

        # Condition key dropdown
        dd = ttk.Combobox(frame, values=CONDITION_KEYS, width=15)
        dd.set(key)
        dd.pack(side=tk.LEFT)

        # Equal sign
        tk.Label(frame, text="=", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)

        # Smart value field
        val_frame, get_val, rebuild = self.create_value_field(frame, key, val)
        dd.bind("<<ComboboxSelected>>", lambda e: rebuild(dd.get()))

        # Remove button
        btn = tk.Button(frame, text="-", width=2, command=frame.destroy)
        btn.pack(side=tk.LEFT, padx=1)

        # Store references for format_condition_row
        frame.negate = negate
        frame.dd = dd
        frame.get_val = get_val

    def format_condition_row(self, frame):
        val = frame.get_val().strip()
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
        if self.is_event_mode:
            # In event mode, this becomes add_trigger_row
            self.add_trigger_row(evt_str)
            return
            
        frame = tk.Frame(self.events_frame, bg=DARK_BG)
        frame.pack(fill=tk.X)
        key, val = (evt_str.split("=", 1) + [""])[:2] if "=" in evt_str else ("", "")
        dd = ttk.Combobox(frame, values=EVENT_KEYS, width=20)
        dd.set(key)
        dd.pack(side=tk.LEFT)
        tk.Label(frame, text="=", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        val_frame, get_val, rebuild = self.create_value_field(frame, key, val)
        dd.bind("<<ComboboxSelected>>", lambda e: rebuild(dd.get()))
        frame.get_val = get_val
        btn = tk.Button(frame, text="-", width=2, command=frame.destroy)
        btn.pack(side=tk.LEFT, padx=1)

        frame.dd = dd

    def add_trigger_row(self, trigger_val="on_step"):
        # Clear existing trigger rows (should only be one)
        for w in self.events_frame.winfo_children():
            w.destroy()
            
        frame = tk.Frame(self.events_frame, bg=DARK_BG)
        frame.pack(fill=tk.X)
        
        tk.Label(frame, text="Trigger:", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        
        dd = ttk.Combobox(frame, values=TRIGGER_OPTIONS, width=20, state="readonly")
        dd.set(trigger_val if trigger_val in TRIGGER_OPTIONS else "on_step")
        dd.pack(side=tk.LEFT)
        
        frame.dd = dd
        frame.get_val = lambda: dd.get()

    def format_event_row(self, frame):
        val = frame.get_val().strip()
        key = frame.dd.get().strip()
        if not key: return ""
        return f"{key}={val}"
        
    def format_trigger_row(self, frame):
        return frame.get_val().strip()
    
    def add_alias_mapping_row(self, alias_val="", context_val=""):
        if self.is_event_mode:
            return  # No aliases in event mode
            
        frame = tk.Frame(self.aliases_frame, bg=DARK_BG)
        frame.pack(fill=tk.X, pady=1)

        # Alias entry
        all_keywords = [k for k in self.data[self.current_npc].keys() if isinstance(self.data[self.current_npc][k], list)]
        alias_dd = ttk.Combobox(frame, values=all_keywords, width=15)
        alias_dd.set(alias_val)
        alias_dd.pack(side=tk.LEFT)

        # Current keyword label (not editable)
        tk.Label(frame, text="→", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        tk.Label(frame, text=self.current_keyword, bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)

        # Context combobox (optional)
        tk.Label(frame, text="if last keyword was", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        ctx_dd = ttk.Combobox(frame, values=all_keywords, width=15)
        ctx_dd.set(context_val)
        ctx_dd.pack(side=tk.LEFT)

        # Remove button
        btn = tk.Button(frame, text="-", command=frame.destroy)
        btn.pack(side=tk.LEFT)

        frame.alias_ent = alias_dd
        frame.ctx_dd = ctx_dd

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

def scan_flags_and_quests():
    flags = set()
    quests = {}

    # --- Scan events and dialog for flags ---
    import os, re, json
    for folder in ("events", "dialog"):
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for fname in files:
                if fname.endswith(".json"):
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        text = json.dumps(data)
                        
                        # Find flags with equals sign (existing pattern)
                        for match in re.findall(r'!?flag=([\w\-\.:]+)', text):
                            for x in match.split("|"):
                                flags.add(x)
                        
                        # Find standalone flags in conditions arrays
                        # This pattern looks for items in arrays that don't contain '='
                        conditions_pattern = r'"conditions":\s*\[(.*?)\]'
                        for conditions_match in re.findall(conditions_pattern, text, re.DOTALL):
                            # Extract individual condition items
                            condition_items = re.findall(r'"([^"]*)"', conditions_match)
                            for condition in condition_items:
                                # If it doesn't contain '=' and isn't empty, treat as standalone flag
                                if '=' not in condition and condition.strip():
                                    # Remove leading '!' if present for consistent flag storage
                                    clean_flag = condition.lstrip('!')
                                    flags.add(clean_flag)
                                    
                    except Exception as e:
                        print(f"Error reading {path}: {e}")

    # --- Parse quests.json (or all .json in quests folder) ---
    qfolder = "quests"
    if os.path.isdir(qfolder):
        for fname in os.listdir(qfolder):
            if fname.endswith(".json"):
                path = os.path.join(qfolder, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        for qid, qdata in data.items():
                            steps = list(qdata.get("steps", {}).keys())
                            hints = list(qdata.get("hints", {}).keys())
                            quests[qid] = {"steps": steps, "hints": hints}
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    return sorted(flags), quests

def calculate_text_widget_width(font_name = "georgia", font_size = 24, max_pixel_width = 920):
    """
    Returns the width (in characters) for a Tkinter Text widget
    to fit text of a given font inside max_pixel_width.
    """
    root = tk.Tk()
    root.withdraw()  # hide root window
    
    # Create a Font object
    f = font.Font(family=font_name, size=font_size)
    
    # Measure the width of a typical character
    # '0' is usually a good average-width representative
    char_width = f.measure('0')
    
    # Compute how many characters fit
    widget_width = max(1, int(max_pixel_width / char_width))
    
    root.destroy()
    print(widget_width)
    return widget_width

if __name__ == "__main__":
    app = DialogEditor()
    app.mainloop()