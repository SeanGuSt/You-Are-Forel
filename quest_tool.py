import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
completion_options = ["i", "a", "c", "f"]

class QuestEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Quest JSON Editor")
        self.root.geometry("1200x700+200+50")
        
        self.quest_data = {}
        self.current_file = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Left panel - Quest list
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)
        
        ttk.Label(left_frame, text="Quests", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=(0, 5))
        
        # Quest listbox with scrollbar
        quest_frame = ttk.Frame(left_frame)
        quest_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        quest_frame.columnconfigure(0, weight=1)
        quest_frame.rowconfigure(0, weight=1)
        
        self.quest_listbox = tk.Listbox(quest_frame, width=30)
        quest_scrollbar = ttk.Scrollbar(quest_frame, orient="vertical", command=self.quest_listbox.yview)
        self.quest_listbox.configure(yscrollcommand=quest_scrollbar.set)
        
        self.quest_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        quest_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.quest_listbox.bind('<<ListboxSelect>>', self.on_quest_select)
        
        # Quest management buttons
        quest_btn_frame = ttk.Frame(left_frame)
        quest_btn_frame.grid(row=2, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(quest_btn_frame, text="Add Quest", command=self.add_quest).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(quest_btn_frame, text="Delete Quest", command=self.delete_quest).grid(row=0, column=1)
        
        # Right panel - Quest details
        self.right_frame = ttk.Frame(main_frame)
        self.right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=1)
        
        self.setup_quest_details()
        
    def setup_quest_details(self):
        # Clear existing widgets
        for widget in self.right_frame.winfo_children():
            widget.destroy()
            
        # Notebook for different sections
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Basic Info Tab
        self.basic_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.basic_frame, text="Basic Info")
        
        # Quest ID
        ttk.Label(self.basic_frame, text="Quest ID:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.quest_id_var = tk.StringVar()
        self.quest_id_entry = ttk.Entry(self.basic_frame, textvariable=self.quest_id_var, width=40)
        self.quest_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.quest_id_entry.bind('<FocusOut>', self.on_quest_id_change)
        
        # Quest Name
        ttk.Label(self.basic_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.quest_name_var = tk.StringVar()
        ttk.Entry(self.basic_frame, textvariable=self.quest_name_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Quest Description
        ttk.Label(self.basic_frame, text="Description:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.quest_desc_text = scrolledtext.ScrolledText(self.basic_frame, height=4, width=50)
        self.quest_desc_text.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.basic_frame.columnconfigure(1, weight=1)
        
        # Steps Tab
        self.steps_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.steps_frame, text="Steps")
        self.setup_steps_tab()
        
        # Hints Tab
        self.hints_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.hints_frame, text="Hints")
        self.setup_hints_tab()
        
        # Rewards Tab
        self.rewards_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.rewards_frame, text="Rewards")
        self.setup_rewards_tab()
        
    def setup_steps_tab(self):
        self.steps_frame.columnconfigure(0, weight=1)
        self.steps_frame.rowconfigure(1, weight=1)
        
        # Steps list
        steps_list_frame = ttk.Frame(self.steps_frame)
        steps_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        steps_list_frame.columnconfigure(0, weight=1)
        
        ttk.Label(steps_list_frame, text="Steps:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        
        self.steps_listbox = tk.Listbox(steps_list_frame, height=6)
        self.steps_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.steps_listbox.bind('<<ListboxSelect>>', self.on_step_select)
        
        # Step buttons
        step_btn_frame = ttk.Frame(self.steps_frame)
        step_btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        ttk.Button(step_btn_frame, text="Add Step", command=self.add_step).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(step_btn_frame, text="Delete Step", command=self.delete_step).grid(row=0, column=1)
        
        # Step details
        step_details_frame = ttk.LabelFrame(self.steps_frame, text="Step Details", padding="10")
        step_details_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        step_details_frame.columnconfigure(1, weight=1)
        
        ttk.Label(step_details_frame, text="Step ID:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.step_id_var = tk.StringVar()
        self.step_id_entry = ttk.Entry(step_details_frame, textvariable=self.step_id_var, width=30)
        self.step_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(step_details_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.step_name_var = tk.StringVar()
        ttk.Entry(step_details_frame, textvariable=self.step_name_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(step_details_frame, text="Description:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.step_desc_text = scrolledtext.ScrolledText(step_details_frame, height=3, width=40)
        self.step_desc_text.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(step_details_frame, text="Vague Description:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.step_vague_desc_text = scrolledtext.ScrolledText(step_details_frame, height=2, width=40)
        self.step_vague_desc_text.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.step_status_var = tk.StringVar(value="i")  
        # Dropdown menu  
        label = ttk.Label(step_details_frame, text="Initial Step Status:")
        label.grid(row=4, column=0, pady=(0, 5), sticky=(tk.W, tk.N))
        ttk.OptionMenu(step_details_frame, self.step_status_var, *completion_options).grid(row=4, column=1, sticky=(tk.W, tk.N), pady=(0, 5))
        
        ttk.Button(step_details_frame, text="Save Step", command=self.save_step).grid(row=5, column=1, sticky=tk.E, pady=(10, 0))
        
    def setup_hints_tab(self):
        self.hints_frame.columnconfigure(0, weight=1)
        self.hints_frame.rowconfigure(1, weight=1)
        
        # Hints list
        hints_list_frame = ttk.Frame(self.hints_frame)
        hints_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        hints_list_frame.columnconfigure(0, weight=1)
        
        ttk.Label(hints_list_frame, text="Hints:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W)
        
        self.hints_listbox = tk.Listbox(hints_list_frame, height=6)
        self.hints_listbox.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.hints_listbox.bind('<<ListboxSelect>>', self.on_hint_select)
        
        # Hint buttons
        hint_btn_frame = ttk.Frame(self.hints_frame)
        hint_btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        ttk.Button(hint_btn_frame, text="Add Hint", command=self.add_hint).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(hint_btn_frame, text="Delete Hint", command=self.delete_hint).grid(row=0, column=1)
        
        # Hint details
        hint_details_frame = ttk.LabelFrame(self.hints_frame, text="Hint Details", padding="10")
        hint_details_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        hint_details_frame.columnconfigure(1, weight=1)
        
        ttk.Label(hint_details_frame, text="Hint ID:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.hint_id_var = tk.StringVar()
        self.hint_id_entry = ttk.Entry(hint_details_frame, textvariable=self.hint_id_var, width=30)
        self.hint_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(hint_details_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.hint_name_var = tk.StringVar()
        ttk.Entry(hint_details_frame, textvariable=self.hint_name_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(hint_details_frame, text="Description:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        self.hint_desc_text = scrolledtext.ScrolledText(hint_details_frame, height=4, width=40)
        self.hint_desc_text.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.hint_status_var = tk.StringVar(value="i")  
        # Dropdown menu
        label = ttk.Label(hint_details_frame, text="Initial Hint Status:")
        label.grid(row=4, column=0, pady=(0, 5), sticky=(tk.W, tk.N))  
        ttk.OptionMenu(hint_details_frame, self.hint_status_var, *completion_options).grid(row=4, column=1, sticky=(tk.W, tk.N), pady=(0, 5))
        
        ttk.Button(hint_details_frame, text="Save Hint", command=self.save_hint).grid(row=4, column=1, sticky=tk.E, pady=(10, 0))
        
    def setup_rewards_tab(self):
        self.rewards_frame.columnconfigure(0, weight=1)
        
        # XP
        ttk.Label(self.rewards_frame, text="Experience Points:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.xp_var = tk.StringVar()
        ttk.Entry(self.rewards_frame, textvariable=self.xp_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        
        # Gold
        ttk.Label(self.rewards_frame, text="Gold:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.gold_var = tk.StringVar()
        ttk.Entry(self.rewards_frame, textvariable=self.gold_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        
        # Items
        ttk.Label(self.rewards_frame, text="Items:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=(0, 5))
        
        items_frame = ttk.Frame(self.rewards_frame)
        items_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        items_frame.columnconfigure(0, weight=1)
        
        self.items_text = scrolledtext.ScrolledText(items_frame, height=8, width=50)
        self.items_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Help text for items format
        help_frame = ttk.LabelFrame(self.rewards_frame, text="Item Format Help", padding="10")
        help_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        help_text = """Item Format Examples:
• sword_of_fire__2 (item with quantity 2)
• magic_potion (single item, quantity 1)
• rare_gem__5 | common_stone__10 (random choice between items)
• legendary_sword--1 | epic_sword--3 | rare_sword--6 (weighted random choice)

Use one item per line. __ separates item name and quantity.
| separates random choices. -- separates item and weight."""
        
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, wraplength=600).grid(row=0, column=0, sticky=tk.W)
        
    def new_file(self):
        if self.quest_data and messagebox.askyesno("New File", "Unsaved changes will be lost. Continue?"):
            self.quest_data = {}
            self.current_file = None
            self.refresh_quest_list()
            self.clear_quest_details()
            
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open Quest File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.quest_data = json.load(f)
                self.current_file = file_path
                self.refresh_quest_list()
                self.clear_quest_details()
                messagebox.showinfo("Success", f"Loaded {len(self.quest_data)} quests")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                
    def save_file(self):
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_as_file()
            
    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Quest File",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self.save_to_file(file_path)
            self.current_file = file_path
            
    def save_to_file(self, file_path):
        try:
            # Save current quest details before saving file
            self.save_current_quest_details()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.quest_data, f, indent=4)
            messagebox.showinfo("Success", f"Saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
            
    def refresh_quest_list(self):
        self.quest_listbox.delete(0, tk.END)
        for quest_id in self.quest_data.keys():
            quest_name = self.quest_data[quest_id].get('name', quest_id)
            self.quest_listbox.insert(tk.END, f"{quest_id}: {quest_name}")
            
    def add_quest(self):
        quest_id = tk.simpledialog.askstring("Add Quest", "Enter Quest ID:")
        if quest_id and quest_id not in self.quest_data:
            self.quest_data[quest_id] = {
                "name": "New Quest",
                "description": "",
                "steps": {},
                "hints": {},
                "reward": {}
            }
            self.refresh_quest_list()
            # Select the new quest
            for i in range(self.quest_listbox.size()):
                if self.quest_listbox.get(i).startswith(quest_id + ":"):
                    self.quest_listbox.selection_set(i)
                    self.on_quest_select(None)
                    break
        elif quest_id:
            messagebox.showerror("Error", "Quest ID already exists!")
            
    def delete_quest(self):
        selection = self.quest_listbox.curselection()
        if selection:
            quest_entry = self.quest_listbox.get(selection[0])
            quest_id = quest_entry.split(":")[0]
            
            if messagebox.askyesno("Delete Quest", f"Delete quest '{quest_id}'?"):
                del self.quest_data[quest_id]
                self.refresh_quest_list()
                self.clear_quest_details()
                
    def on_quest_select(self, event):
        selection = self.quest_listbox.curselection()
        if selection:
            quest_entry = self.quest_listbox.get(selection[0])
            quest_id = quest_entry.split(":")[0]
            self.load_quest_details(quest_id)
            
    def load_quest_details(self, quest_id):
        if quest_id not in self.quest_data:
            return
            
        quest = self.quest_data[quest_id]
        
        # Load basic info
        self.quest_id_var.set(quest_id)
        self.quest_name_var.set(quest.get('name', ''))
        self.quest_desc_text.delete('1.0', tk.END)
        self.quest_desc_text.insert('1.0', quest.get('description', ''))
        
        # Load steps
        self.refresh_steps_list(quest.get('steps', {}))
        
        # Load hints
        self.refresh_hints_list(quest.get('hints', {}))
        
        # Load rewards
        reward = quest.get('reward', {})
        self.xp_var.set(str(reward.get('xp', '')))
        self.gold_var.set(str(reward.get('gold', '')))
        
        # Format items
        items_text = ""
        if 'item' in reward:
            items_text = reward['item']
        elif 'items' in reward:
            items_text = "\n".join(reward['items'])
            
        self.items_text.delete('1.0', tk.END)
        self.items_text.insert('1.0', items_text)
        
        self.clear_step_details()
        self.clear_hint_details()
        
    def refresh_steps_list(self, steps):
        self.steps_listbox.delete(0, tk.END)
        for step_id, step_data in steps.items():
            step_name = step_data.get('name', step_id)
            self.steps_listbox.insert(tk.END, f"{step_id}: {step_name}")
            
    def refresh_hints_list(self, hints):
        self.hints_listbox.delete(0, tk.END)
        for hint_id, hint_data in hints.items():
            hint_name = hint_data.get('name', hint_id)
            self.hints_listbox.insert(tk.END, f"{hint_id}: {hint_name}")
            
    def on_step_select(self, event):
        selection = self.steps_listbox.curselection()
        if selection:
            step_entry = self.steps_listbox.get(selection[0])
            step_id = step_entry.split(":")[0]
            self.load_step_details(step_id)
            
    def on_hint_select(self, event):
        selection = self.hints_listbox.curselection()
        if selection:
            hint_entry = self.hints_listbox.get(selection[0])
            hint_id = hint_entry.split(":")[0]
            self.load_hint_details(hint_id)
            
    def load_step_details(self, step_id):
        quest_id = self.quest_id_var.get()
        if quest_id not in self.quest_data:
            return
            
        steps = self.quest_data[quest_id].get('steps', {})
        if step_id not in steps:
            return
            
        step = steps[step_id]
        self.step_id_var.set(step_id)
        self.step_name_var.set(step.get('name', ''))
        
        self.step_desc_text.delete('1.0', tk.END)
        self.step_desc_text.insert('1.0', step.get('description', ''))
        
        self.step_vague_desc_text.delete('1.0', tk.END)
        self.step_vague_desc_text.insert('1.0', step.get('description_vague', ''))
        
        self.step_status_var.set(step.get('status', "i"))
        
    def load_hint_details(self, hint_id):
        quest_id = self.quest_id_var.get()
        if quest_id not in self.quest_data:
            return
            
        hints = self.quest_data[quest_id].get('hints', {})
        if hint_id not in hints:
            return
            
        hint = hints[hint_id]
        self.hint_id_var.set(hint_id)
        self.hint_name_var.set(hint.get('name', ''))
        
        self.hint_desc_text.delete('1.0', tk.END)
        self.hint_desc_text.insert('1.0', hint.get('description', ''))
        
        self.hint_status_var.set(hint.get('status', "i"))
        
    def add_step(self):
        step_id = tk.simpledialog.askstring("Add Step", "Enter Step ID:")
        quest_id = self.quest_id_var.get()
        
        if step_id and quest_id and quest_id in self.quest_data:
            if 'steps' not in self.quest_data[quest_id]:
                self.quest_data[quest_id]['steps'] = {}
                
            if step_id not in self.quest_data[quest_id]['steps']:
                self.quest_data[quest_id]['steps'][step_id] = {
                    "name": "New Step",
                    "description": ""
                }
                self.refresh_steps_list(self.quest_data[quest_id]['steps'])
            else:
                messagebox.showerror("Error", "Step ID already exists!")
                
    def add_hint(self):
        hint_id = tk.simpledialog.askstring("Add Hint", "Enter Hint ID:")
        quest_id = self.quest_id_var.get()
        
        if hint_id and quest_id and quest_id in self.quest_data:
            if 'hints' not in self.quest_data[quest_id]:
                self.quest_data[quest_id]['hints'] = {}
                
            if hint_id not in self.quest_data[quest_id]['hints']:
                self.quest_data[quest_id]['hints'][hint_id] = {
                    "name": "New Hint",
                    "description": ""
                }
                self.refresh_hints_list(self.quest_data[quest_id]['hints'])
            else:
                messagebox.showerror("Error", "Hint ID already exists!")
                
    def delete_step(self):
        selection = self.steps_listbox.curselection()
        quest_id = self.quest_id_var.get()
        
        if selection and quest_id:
            step_entry = self.steps_listbox.get(selection[0])
            step_id = step_entry.split(":")[0]
            
            if messagebox.askyesno("Delete Step", f"Delete step '{step_id}'?"):
                del self.quest_data[quest_id]['steps'][step_id]
                self.refresh_steps_list(self.quest_data[quest_id]['steps'])
                self.clear_step_details()
                
    def delete_hint(self):
        selection = self.hints_listbox.curselection()
        quest_id = self.quest_id_var.get()
        
        if selection and quest_id:
            hint_entry = self.hints_listbox.get(selection[0])
            hint_id = hint_entry.split(":")[0]
            
            if messagebox.askyesno("Delete Hint", f"Delete hint '{hint_id}'?"):
                del self.quest_data[quest_id]['hints'][hint_id]
                self.refresh_hints_list(self.quest_data[quest_id]['hints'])
                self.clear_hint_details()
                
    def save_step(self):
        quest_id = self.quest_id_var.get()
        step_id = self.step_id_var.get()
        
        if quest_id and step_id and quest_id in self.quest_data:
            step_data = {
                "name": self.step_name_var.get(),
                "description": self.step_desc_text.get('1.0', tk.END).strip()
            }
            
            vague_desc = self.step_vague_desc_text.get('1.0', tk.END).strip()
            if vague_desc:
                step_data["description_vague"] = vague_desc
            step_status = self.step_status_var.get()    
            if step_status:
                step_data["status"] = step_status
                
            self.quest_data[quest_id]['steps'][step_id] = step_data
            self.refresh_steps_list(self.quest_data[quest_id]['steps'])
            messagebox.showinfo("Success", "Step saved!")
            
    def save_hint(self):
        quest_id = self.quest_id_var.get()
        hint_id = self.hint_id_var.get()
        
        if quest_id and hint_id and quest_id in self.quest_data:
            hint_data = {
                "name": self.hint_name_var.get(),
                "description": self.hint_desc_text.get('1.0', tk.END).strip()
            }
            
            hint_status = self.hint_status_var.get()
            if hint_status:
                hint_data["status"] = hint_status
                
            self.quest_data[quest_id]['hints'][hint_id] = hint_data
            self.refresh_hints_list(self.quest_data[quest_id]['hints'])
            messagebox.showinfo("Success", "Hint saved!")
            
    def save_current_quest_details(self):
        """Save the current quest details from the form to the data structure"""
        quest_id = self.quest_id_var.get()
        if not quest_id or quest_id not in self.quest_data:
            return
            
        quest = self.quest_data[quest_id]
        
        # Save basic info
        quest['name'] = self.quest_name_var.get()
        quest['description'] = self.quest_desc_text.get('1.0', tk.END).strip()
        
        # Save rewards
        reward = {}
        
        if self.xp_var.get().strip():
            try:
                reward['xp'] = int(self.xp_var.get())
            except ValueError:
                pass
                
        if self.gold_var.get().strip():
            try:
                reward['gold'] = int(self.gold_var.get())
            except ValueError:
                pass
                
        items_text = self.items_text.get('1.0', tk.END).strip()
        if items_text:
            items = [line.strip() for line in items_text.split('\n') if line.strip()]
            if len(items) == 1:
                reward['item'] = items[0]
            elif len(items) > 1:
                reward['items'] = items
                
        if reward:
            quest['reward'] = reward
        elif 'reward' in quest:
            del quest['reward']
            
    def on_quest_id_change(self, event):
        """Handle quest ID changes (renaming quests)"""
        old_id = None
        selection = self.quest_listbox.curselection()
        if selection:
            quest_entry = self.quest_listbox.get(selection[0])
            old_id = quest_entry.split(":")[0]
            
        new_id = self.quest_id_var.get()
        
        if old_id and old_id != new_id and old_id in self.quest_data:
            if new_id in self.quest_data:
                messagebox.showerror("Error", "Quest ID already exists!")
                self.quest_id_var.set(old_id)
                return
                
            # Rename the quest
            self.quest_data[new_id] = self.quest_data.pop(old_id)
            self.refresh_quest_list()
            
            # Reselect the renamed quest
            for i in range(self.quest_listbox.size()):
                if self.quest_listbox.get(i).startswith(new_id + ":"):
                    self.quest_listbox.selection_set(i)
                    break
                    
    def clear_quest_details(self):
        """Clear all quest detail fields"""
        self.quest_id_var.set("")
        self.quest_name_var.set("")
        self.quest_desc_text.delete('1.0', tk.END)
        
        self.steps_listbox.delete(0, tk.END)
        self.hints_listbox.delete(0, tk.END)
        
        self.xp_var.set("")
        self.gold_var.set("")
        self.items_text.delete('1.0', tk.END)
        
        self.clear_step_details()
        self.clear_hint_details()
        
    def clear_step_details(self):
        """Clear step detail fields"""
        self.step_id_var.set("")
        self.step_name_var.set("")
        self.step_desc_text.delete('1.0', tk.END)
        self.step_vague_desc_text.delete('1.0', tk.END)
        self.step_status_var.set("i")
        
    def clear_hint_details(self):
        """Clear hint detail fields"""
        self.hint_id_var.set("")
        self.hint_name_var.set("")
        self.hint_desc_text.delete('1.0', tk.END)
        self.hint_status_var.set("i")


def main():
    # Import tkinter.simpledialog here to avoid issues if it's not available
    import tkinter.simpledialog
    
    root = tk.Tk()
    app = QuestEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()