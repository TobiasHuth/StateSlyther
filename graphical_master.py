import tkinter as tk
from tkinter import ttk
import xml.etree.ElementTree as ET
import tkinter.filedialog as fd
from code_generators import show_code_editor

class GraphicalMaster(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Graphical Master")
        self.geometry("900x600")
        self.mode = "select"  # modes: select, state, junction, line
        self._temp = None
        self._start = None
        self.selected = None
        self._drag_start = None
        self._dragging = False  # Track if actual dragging is occurring
        self._clicked_text_id = None  # Track if text was clicked
        self._clicked_code_id = None  # Track if code was clicked
        self._clicked_condition_id = None  # Track if condition was clicked
        self.default_state = None  # Track the default state
        self.language_var = tk.StringVar(value="python")  # Track the code generation language
        self.language = "python"  # Track the code generation language
        self.edges = {}  # Track edges with their conditions: edge_id -> {'condition': str, 'condition_text_id': id, ...}
        self.nodes = {}  # item_id: {'position': (x,y), 'size': (w,h), 'type': 'state'/'junction', 'name': str, 'text_id': item_id, 'incoming': [edge_ids], 'outgoing': [edge_ids], 'incoming_points': {edge_id: (rel_x, rel_y)}, 'outgoing_points': {edge_id: (rel_x, rel_y)}}
        self._resize_handle = None
        self._pan_start = None  # Track pan start position for middle mouse button

        self._build_ui()

    def _build_ui(self):
        # Create menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_layout)
        file_menu.add_command(label="Open", command=self.open_layout)
        
        # Chart menu
        chart_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Chart", menu=chart_menu)
        chart_menu.add_command(label="Show Connections", command=self.show_connections)
        chart_menu.add_command(label="Clear", command=lambda: self.canvas.delete("shape"))
        
        # Code menu
        code_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Code", menu=code_menu)
        
        # Language submenu
        language_menu = tk.Menu(code_menu, tearoff=0)
        code_menu.add_cascade(label="Set Language", menu=language_menu)
        language_menu.add_radiobutton(label="Python", variable=self.language_var, value="python", command=lambda: self.set_language("python"))
        language_menu.add_radiobutton(label="C", variable=self.language_var, value="C", command=lambda: self.set_language("C"))
        
        code_menu.add_command(label="Update/Show Code", command=self.show_generated_code)
        
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x")

        for m in ("state", "junction", "line"):
            btn = ttk.Button(toolbar, text=m.capitalize(), command=lambda mm=m: self.set_mode(mm))
            btn.pack(side="left", padx=4, pady=4)

        self.default_btn = ttk.Button(toolbar, text="Set as Default", command=self.set_default_state, state="disabled")
        self.default_btn.pack(side="left", padx=4)

        # Create canvas frame with scrollbars
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)
        
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Create canvas with scrollbar configuration
        self.canvas = tk.Canvas(canvas_frame, bg="white", cursor="arrow", yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        self.canvas.pack(fill="both", expand=True, side="left")
        
        # Configure scrollbars to work with canvas
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Configure canvas scrolling region with large initial area to allow expansion
        self.canvas.config(scrollregion="-5000 -5000 5000 5000")

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        # self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", lambda event: self.set_mode("select"))
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-2>", self.on_pan_end)
        self.bind("<Delete>", lambda event: self.delete_selected())
        self.bind("<space>", lambda event: self.focus_diagram())

    def update_scroll_region(self):
        """Update the canvas scroll region to fit all content with padding."""
        bbox = self.canvas.bbox("all")
        if bbox:
            # Add padding around content
            padding = 500
            scroll_region = (
                int(bbox[0] - padding),
                int(bbox[1] - padding),
                int(bbox[2] + padding),
                int(bbox[3] + padding)
            )
        else:
            # Default large area if no content
            scroll_region = "-5000 -5000 5000 5000"
        self.canvas.config(scrollregion=scroll_region)

    def on_pan_start(self, event):
        """Start panning - store the initial mouse position and clear other states."""
        # Clear any previous interaction states to prevent interference
        self._drag_start = None
        self._dragging = False
        self._clicked_text_id = None
        self._clicked_code_id = None
        self._clicked_condition_id = None
        self._resize_handle = None
        self._temp = None
        self._pan_start = (event.x, event.y)
        self.canvas.config(cursor="hand2")

    def on_pan_move(self, event):
        """Pan the canvas by scrolling based on mouse movement."""
        if self._pan_start:
            # Calculate the distance moved in pixels
            dx = event.x - self._pan_start[0]
            dy = event.y - self._pan_start[1]
            
            # Get the current scroll position
            x_view = self.canvas.xview()
            y_view = self.canvas.yview()
            
            # Get scroll region and canvas dimensions
            scroll_region = self.canvas.cget("scrollregion").split()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if scroll_region and canvas_width > 1 and canvas_height > 1:
                region_width = float(scroll_region[2]) - float(scroll_region[0])
                region_height = float(scroll_region[3]) - float(scroll_region[1])
                
                # Calculate new scroll position based on pixel movement
                new_x = x_view[0] - (dx / region_width)  
                new_y = y_view[0] - (dy / region_height) 

                # Clamp values to valid range [0, 1]
                new_x = max(0, min(1, new_x))
                new_y = max(0, min(1, new_y))
                
                # Apply the new scroll position
                self.canvas.xview_moveto(new_x)
                self.canvas.yview_moveto(new_y)
            
            # Update pan start position for next movement
            self._pan_start = (event.x, event.y)

    def on_pan_end(self, event):
        """End panning."""
        self._pan_start = None
        self.canvas.config(cursor="arrow")

    def focus_diagram(self):
        """Pan to show the top-left most item of the diagram in the top-left corner of the visible canvas."""
        bbox = self.canvas.bbox("all")
        if bbox:
            # Get scroll region
            scroll_region = self.canvas.cget("scrollregion").split()
            region_x0 = float(scroll_region[0])
            region_y0 = float(scroll_region[1])
            region_width = float(scroll_region[2]) - region_x0
            region_height = float(scroll_region[3]) - region_y0
            
            # Get top-left corner of the diagram
            top_left_x = bbox[0]
            top_left_y = bbox[1]
            
            # Calculate scroll position as fraction [0, 1]
            scroll_x = (top_left_x - region_x0) / region_width
            scroll_y = (top_left_y - region_y0) / region_height
            
            # Clamp to valid range
            scroll_x = max(0, min(1, scroll_x))
            scroll_y = max(0, min(1, scroll_y))
            
            # Apply scroll position
            self.canvas.xview_moveto(scroll_x)
            self.canvas.yview_moveto(scroll_y)

    def set_mode(self, mode):
        self.mode = mode
        self._deselect()
        # Update cursor based on mode
        if mode == "select":
            self.canvas.config(cursor="arrow")
        elif mode == "line":
            self.canvas.config(cursor="crosshair")
        elif mode in ("state", "junction"):
            self.canvas.config(cursor="cross")

    def _point_to_bbox_distance(self, bbox, x, y):
        if not bbox:
            return float("inf")
        x0, y0, x1, y1 = bbox
        dx = 0 if x0 <= x <= x1 else (x0 - x if x < x0 else x - x1)
        dy = 0 if y0 <= y <= y1 else (y0 - y if y < y0 else y - y1)
        return (dx*dx + dy*dy) ** 0.5

    def _is_close(self, item_id, x, y, max_distance=15):
        bbox = self.canvas.bbox(item_id)
        return self._point_to_bbox_distance(bbox, x, y) <= max_distance

    def _closest_point_on_bbox(self, bbox, x, y):
        if not bbox:
            return x, y
        x0, y0, x1, y1 = bbox
        # Clamp x and y to the bbox
        cx = max(x0, min(x, x1))
        cy = max(y0, min(y, y1))
        return cx, cy

    def on_mouse_down(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.mode == "select":
            item = self.canvas.find_closest(x, y)
            if item and "edge" in self.canvas.gettags(item):
                # Select the edge when clicking on the line (but don't enable dragging)
                self.select(item[0])
            elif item and "condition" in self.canvas.gettags(item):
                # Mark that condition was clicked for editing
                self._clicked_condition_id = item[0]
                # Find the edge this condition belongs to
                for edge_id, edge_data in self.edges.items():
                    if 'condition_text_id' in edge_data and edge_data['condition_text_id'] == item[0]:
                        self.select(edge_id)
                        # Don't set _drag_start for edges - they should not be draggable
                        break
            elif item and "text" in self.canvas.gettags(item):
                # Mark that text was clicked, but don't rename yet
                self._clicked_text_id = item[0]
            elif item and "code" in self.canvas.gettags(item):
                # Mark that code was clicked for editing
                self._clicked_code_id = item[0]
                # Find the parent state and enable dragging
                for node_id, node_data in self.nodes.items():
                    if 'code_id' in node_data and node_data['code_id'] == item[0]:
                        self.select(node_id)
                        self._drag_start = (x, y)
                        break
            elif item and "node" in self.canvas.gettags(item):
                corner_resize_size = 10
                if self._is_close(item[0], x, y, max_distance=corner_resize_size):
                    self.select(item[0])
                    self._drag_start = (x, y)
                    # Check if clicking on resize handle (any corner)
                    bbox = self.canvas.bbox(item[0])
                    if abs(x - bbox[2]) < corner_resize_size and abs(y - bbox[3]) < corner_resize_size:
                        self._resize_handle = 'br'
                    else:
                        self._resize_handle = None
                else:
                    self._deselect()
            else:
                self._deselect()
        elif self.mode == "line":
            # Check if starting on a shape
            item = self.canvas.find_closest(x, y)
            if item and "node" in self.canvas.gettags(item) and self._is_close(item[0], x, y, max_distance=15):
                bbox = self.canvas.bbox(item[0])
                start_x, start_y = self._closest_point_on_bbox(bbox, x, y)
                self._start = (start_x, start_y)
                self._start_shape = item[0]
            else:
                self._start = None
                self._start_shape = None
        else:
            self._start = (x, y)
            if self.mode == "state":
                self._temp = self.canvas.create_rectangle(x, y, x+350, y+150, outline="black", tags=("shape","node","temp"))
            elif self.mode == "junction":
                self._temp = self.canvas.create_oval(x, y, x, y, outline="black", tags=("shape","node","temp"))

    def on_mouse_move(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        # If dragging occurs, set flag and clear the clicked flags
        if self._drag_start:
            self._dragging = True
            self._clicked_text_id = None
            self._clicked_code_id = None
            self._clicked_condition_id = None
        
        if self.mode == "select" and self.selected and self._drag_start:
            dx = x - self._drag_start[0]
            dy = y - self._drag_start[1]
            if self._resize_handle:
                bbox = self.canvas.bbox(self.selected)
                if self._resize_handle == 'br':
                    new_x0, new_y0 = bbox[0], bbox[1]
                    new_x1, new_y1 = x, y
                else:
                    new_x0, new_y0 = bbox[0] + dx, bbox[1]
                    new_x1, new_y1 = bbox[2], bbox[3]
                min_size_x = 100 if self.nodes[self.selected]['type'] == 'state' else 20
                min_size_y = 30 if self.nodes[self.selected]['type'] == 'state' else 20
                if new_x1 - new_x0 < min_size_x:
                    if self._resize_handle in ('br', 'tr'):
                        new_x1 = new_x0 + min_size_x
                    else:
                        new_x0 = new_x1 - min_size_x
                if new_y1 - new_y0 < min_size_y:
                    if self._resize_handle in ('br', 'bl'):
                        new_y1 = new_y0 + min_size_y
                    else:
                        new_y0 = new_y1 - min_size_y
                self.canvas.coords(self.selected, new_x0, new_y0, new_x1, new_y1)
                new_bbox = self.canvas.bbox(self.selected)
                original_center_x = (bbox[0] + bbox[2]) / 2
                original_center_y = (bbox[1] + bbox[3]) / 2
                new_center_x = (new_bbox[0] + new_bbox[2]) / 2
                new_center_y = (new_bbox[1] + new_bbox[3]) / 2
                dx = original_center_x - new_center_x
                dy = original_center_y - new_center_y
                self.canvas.move(self.selected, dx, dy)
                new_bbox = self.canvas.bbox(self.selected)
                self.nodes[self.selected]['position'] = (new_bbox[0], new_bbox[1])
                self.nodes[self.selected]['size'] = (new_bbox[2] - new_bbox[0], new_bbox[3] - new_bbox[1])
                self.update_edges()
                if self.nodes[self.selected]['type'] == 'state':
                    self.update_text(self.selected)
            else:
                self.canvas.move(self.selected, dx, dy)
                new_bbox = self.canvas.bbox(self.selected)
                self.nodes[self.selected]['position'] = (new_bbox[0], new_bbox[1])
                self.update_edges()
                if self.nodes[self.selected]['type'] == 'state':
                    self.update_text(self.selected)
            self._drag_start = (x, y)
        elif self._temp and self._start:
            x0, y0 = self._start
            if self.mode in ("state", "junction"):
                self.canvas.coords(self._temp, x0, y0, x, y)

    def on_mouse_up(self, event):
        # Check if condition was clicked with minimal movement (no dragging)
        if self._clicked_condition_id and not self._dragging:
            self.edit_condition()
            self._clicked_condition_id = None
            self._dragging = False
            return
        
        # Check if text was clicked with minimal movement (no dragging)
        if self._clicked_text_id and not self._dragging:
            # Find which state this text belongs to
            for node_id, node_data in self.nodes.items():
                if 'text_id' in node_data and node_data['text_id'] == self._clicked_text_id and node_data['type'] == 'state':
                    self.selected = node_id
                    self.rename_selected()
                    self._clicked_text_id = None
                    self._dragging = False
                    return
            self._clicked_text_id = None
        
        # Check if code was clicked with minimal movement (no dragging)
        if self._clicked_code_id and not self._dragging:
            # Find which state this code belongs to
            for node_id, node_data in self.nodes.items():
                if 'code_id' in node_data and node_data['code_id'] == self._clicked_code_id and node_data['type'] == 'state':
                    self.selected = node_id
                    self.edit_code()
                    self._clicked_code_id = None
                    self._dragging = False
                    return
            self._clicked_code_id = None
        
        if self._temp:
            if self.mode == "line":
                # Line mode doesn't use _temp for preview
                pass
            else:
                bbox = self.canvas.bbox(self._temp)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                if self.mode == 'state':
                    w = max(w, 350)
                    h = max(h, 150)
                elif self.mode == 'junction':
                    w = max(w, 20)
                    h = max(h, 20)
                if w != bbox[2] - bbox[0] or h != bbox[3] - bbox[1]:
                    self.canvas.coords(self._temp, bbox[0], bbox[1], bbox[0] + w, bbox[1] + h)
                    bbox = self.canvas.bbox(self._temp)
                self.nodes[self._temp] = {
                    'position': (bbox[0], bbox[1]),
                    'size': (w, h),
                    'type': 'state' if self.mode == 'state' else 'junction',
                    'name': f"State {self._temp}" if self.mode == 'state' else '',
                    'code': "entry:\n// code executed once on entry of the state\nduring:\n// cyclic execution as long as state is active\nexit:\n// code executed when exiting the state\n" if self.mode == 'state' else '',
                    'incoming': [],
                    'outgoing': [],
                    'incoming_points': {},
                    'outgoing_points': {}
                }
                if self.mode == 'state':
                    self.update_text(self._temp)
                    # Set as default state if it's the first state
                    if self.default_state is None:
                        self.default_state = self._temp
                        self.canvas.itemconfig(self._temp, outline="green", width=2)
                self._temp = None
                self._start = None
                self.set_mode("select")
        elif self.mode == "line" and self._start:
            # Check if ending on a different shape
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            item = self.canvas.find_closest(x, y)
            if item and "node" in self.canvas.gettags(item) and item[0] != self._start_shape:
                bbox = self.canvas.bbox(item[0])
                if self._is_close(item[0], x, y, max_distance=15):
                    end_x, end_y = self._closest_point_on_bbox(bbox, x, y)

                    edge_id = self.canvas.create_line(self._start[0], self._start[1], end_x, end_y, fill="black", width=2, arrow="last", tags=("shape","edge", f"start:{self._start_shape}", f"end:{item[0]}"))
                    self.nodes[self._start_shape]['outgoing'].append(edge_id)
                    self.nodes[item[0]]['incoming'].append(edge_id)
                
                    # Store relative points
                    bbox_start = self.canvas.bbox(self._start_shape)
                    rel_start_x = (self._start[0] - bbox_start[0]) / (bbox_start[2] - bbox_start[0])
                    rel_start_y = (self._start[1] - bbox_start[1]) / (bbox_start[3] - bbox_start[1])
                    self.nodes[self._start_shape]['outgoing_points'][edge_id] = (rel_start_x, rel_start_y)
                    
                    rel_end_x = (end_x - bbox[0]) / (bbox[2] - bbox[0])
                    rel_end_y = (end_y - bbox[1]) / (bbox[3] - bbox[1])
                    self.nodes[item[0]]['incoming_points'][edge_id] = (rel_end_x, rel_end_y)
                    
                    # Create condition text at midpoint
                    mid_x = (self._start[0] + end_x) / 2
                    mid_y = (self._start[1] + end_y) / 2
                    
                    condition_code = "//[condition]"
                    condition_color = self.get_condition_text_color(condition_code)
                    # Create condition text with color based on comment symbols
                    condition_text_id = self.canvas.create_text(mid_x, mid_y, text=condition_code, font=("Courier", 9), fill=condition_color, tags=("shape", "condition", f"condition_of:{edge_id}"))
                    
                    # Create gray background rectangle for the text
                    text_bbox = self.canvas.bbox(condition_text_id)
                    if text_bbox:
                        bg_rect_id = self.canvas.create_rectangle(
                            text_bbox[0] - 3, text_bbox[1] - 3, text_bbox[2] + 3, text_bbox[3] + 3,
                            fill="#e9e9e9", outline="#849eaf", tags=("shape", "condition_bg")
                        )
                        # Lower the rectangle behind the text
                        self.canvas.tag_lower(bg_rect_id, condition_text_id)
                    
                    # Store edges as a separate dict entry (not in nodes dict)
                    if not hasattr(self, 'edges'):
                        self.edges = {}
                    self.edges[edge_id] = {
                        'condition': '//[condition]',
                        'condition_text_id': condition_text_id,
                        'condition_bg_id': bg_rect_id if text_bbox else None,
                        'start_pos': (self._start[0], self._start[1]),
                        'end_pos': (end_x, end_y)
                    }
            # If not, do nothing (no line created)
            self._start = None
            self._start_shape = None
        self._drag_start = None
        self._dragging = False
        self._resize_handle = None
        self.update_scroll_region()

    def on_double_click(self, event):
        # quick toggle fill on double click of a shape
        x, y = event.x, event.y
        item = self.canvas.find_closest(x, y)
        if item and "shape" in self.canvas.gettags(item):
            cur = self.canvas.itemcget(item, "fill")
            new = "" if cur else "lightblue"
            self.canvas.itemconfig(item, fill=new)

    def select(self, item_id):
        self._deselect()
        self.selected = item_id
        tags = self.canvas.gettags(item_id)
        if "edge" in tags:
            # Highlight selected edge with thicker line and different color
            self.canvas.itemconfig(item_id, fill="red", width=4)
            self.default_btn.config(state="disabled")
        else:
            # If this is a state, enable the button
            if self.nodes[item_id]['type'] == 'state':
                self.default_btn.config(state="normal")
            else:
                self.default_btn.config(state="disabled")
            
            # If this is the default state, use green outline, otherwise red
            if self.default_state == item_id:
                self.canvas.itemconfig(item_id, outline="green", width=2)
            else:
                self.canvas.itemconfig(item_id, outline="red", width=2)

    def _deselect(self):
        if self.selected:
            try:
                tags = self.canvas.gettags(self.selected)
                if "edge" in tags:
                    # Reset edge to normal appearance
                    self.canvas.itemconfig(self.selected, fill="black", width=2)
                else:
                    # If this is the default state, keep it green, otherwise make it black
                    if self.default_state == self.selected:
                        self.canvas.itemconfig(self.selected, outline="green", width=2)
                    else:
                        self.canvas.itemconfig(self.selected, outline="black", width=1)
            except tk.TclError:
                pass
        self.selected = None
        self.default_btn.config(state="disabled")

    def get_condition_text_color(self, text):
        """Determine text color based on whether condition starts with comment symbol"""
        stripped = text.strip()
        if stripped.startswith(("//", "#", "%")):
            return "#757575"
        return "black"

    def update_edges(self):
        for edge_id in self.canvas.find_withtag("edge"):
            tags = self.canvas.gettags(edge_id)
            start_id = None
            end_id = None
            for tag in tags:
                if tag.startswith("start:"):
                    start_id = int(tag.split(":")[1])
                elif tag.startswith("end:"):
                    end_id = int(tag.split(":")[1])
            if start_id and end_id and start_id in self.nodes and end_id in self.nodes:
                bbox_start = self.canvas.bbox(start_id)
                rel_x, rel_y = self.nodes[start_id]['outgoing_points'][edge_id]
                abs_start_x = bbox_start[0] + rel_x * (bbox_start[2] - bbox_start[0])
                abs_start_y = bbox_start[1] + rel_y * (bbox_start[3] - bbox_start[1])
                
                bbox_end = self.canvas.bbox(end_id)
                rel_x, rel_y = self.nodes[end_id]['incoming_points'][edge_id]
                abs_end_x = bbox_end[0] + rel_x * (bbox_end[2] - bbox_end[0])
                abs_end_y = bbox_end[1] + rel_y * (bbox_end[3] - bbox_end[1])
                
                self.canvas.coords(edge_id, abs_start_x, abs_start_y, abs_end_x, abs_end_y)
                
                # Update condition text position to midpoint
                if edge_id in self.edges and 'condition_text_id' in self.edges[edge_id]:
                    mid_x = (abs_start_x + abs_end_x) / 2
                    mid_y = (abs_start_y + abs_end_y) / 2
                    self.canvas.coords(self.edges[edge_id]['condition_text_id'], mid_x, mid_y)
                    # Update condition background to match text
                    self.update_condition_bg(edge_id)
        self.update_scroll_region()

    def delete_selected(self):
        if self.selected:
            tags = self.canvas.gettags(self.selected)
            if "edge" in tags:
                # Remove from nodes' lists
                for tag in tags:
                    if tag.startswith("start:"):
                        start_id = int(tag.split(":")[1])
                        if self.selected in self.nodes[start_id]['outgoing']:
                            self.nodes[start_id]['outgoing'].remove(self.selected)
                        if self.selected in self.nodes[start_id]['outgoing_points']:
                            del self.nodes[start_id]['outgoing_points'][self.selected]
                    elif tag.startswith("end:"):
                        end_id = int(tag.split(":")[1])
                        if self.selected in self.nodes[end_id]['incoming']:
                            self.nodes[end_id]['incoming'].remove(self.selected)
                        if self.selected in self.nodes[end_id]['incoming_points']:
                            del self.nodes[end_id]['incoming_points'][self.selected]
                # Delete condition text if exists
                if self.selected in self.edges and 'condition_text_id' in self.edges[self.selected]:
                    self.canvas.delete(self.edges[self.selected]['condition_text_id'])
                    if 'condition_bg_id' in self.edges[self.selected] and self.edges[self.selected]['condition_bg_id']:
                        self.canvas.delete(self.edges[self.selected]['condition_bg_id'])
                    del self.edges[self.selected]
            elif "node" in tags:
                # Delete all connected edges
                for edge_id in self.nodes[self.selected]['incoming'] + self.nodes[self.selected]['outgoing']:
                    if edge_id in self.edges and 'condition_text_id' in self.edges[edge_id]:
                        self.canvas.delete(self.edges[edge_id]['condition_text_id'])
                        if 'condition_bg_id' in self.edges[edge_id] and self.edges[edge_id]['condition_bg_id']:
                            self.canvas.delete(self.edges[edge_id]['condition_bg_id'])
                        del self.edges[edge_id]
                    self.canvas.delete(edge_id)
                if 'text_id' in self.nodes[self.selected]:
                    self.canvas.delete(self.nodes[self.selected]['text_id'])
                if 'text_outline_id' in self.nodes[self.selected]:
                    self.canvas.delete(self.nodes[self.selected]['text_outline_id'])
                if 'code_id' in self.nodes[self.selected]:
                    self.canvas.delete(self.nodes[self.selected]['code_id'])
                if 'code_outline_id' in self.nodes[self.selected]:
                    self.canvas.delete(self.nodes[self.selected]['code_outline_id'])
                # If deleting the default state, clear it
                if self.default_state == self.selected:
                    self.default_state = None
                del self.nodes[self.selected]
            self.canvas.delete(self.selected)
            self.selected = None

    def rename_selected(self):
        if self.selected and self.nodes[self.selected]['type'] == 'state':
            import tkinter.simpledialog as sd
            name = sd.askstring("Rename State", "Enter new name:", initialvalue=self.nodes[self.selected]['name'])
            if name is not None:
                self.nodes[self.selected]['name'] = name
                self.update_text(self.selected)

    def edit_code(self):
        if self.selected and self.nodes[self.selected]['type'] == 'state':
            # Create a new window for code editing
            code_window = tk.Toplevel(self)
            code_window.title("Edit Code")
            code_window.geometry("600x400")
            
            # Create button frame first (at the bottom)
            button_frame = ttk.Frame(code_window)
            button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
            
            # Create a text widget for code editing
            text_widget = tk.Text(code_window, font=("Courier", 10), wrap="word")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Insert current code
            text_widget.insert("1.0", self.nodes[self.selected]['code'])
            
            def save_code():
                new_code = text_widget.get("1.0", "end-1c")
                self.nodes[self.selected]['code'] = new_code
                self.update_text(self.selected)
                code_window.destroy()
            
            def cancel_code():
                code_window.destroy()
            
            ttk.Button(button_frame, text="Save", command=save_code).pack(side="left", padx=4)
            ttk.Button(button_frame, text="Cancel", command=cancel_code).pack(side="left", padx=4)

    def edit_condition(self):
        if self.selected and self.selected in self.edges:
            # Create a new window for condition editing
            condition_window = tk.Toplevel(self)
            condition_window.title("Edit Transition Condition")
            condition_window.geometry("400x200")
            
            # Create button frame first (at the bottom)
            button_frame = ttk.Frame(condition_window)
            button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
            
            # Create a text widget for condition editing
            text_widget = tk.Text(condition_window, font=("Courier", 10), wrap="word")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Insert current condition
            text_widget.insert("1.0", self.edges[self.selected]['condition'])
            
            def save_condition():
                new_condition = text_widget.get("1.0", "end-1c")
                self.edges[self.selected]['condition'] = new_condition
                condition_color = self.get_condition_text_color(new_condition)
                self.canvas.itemconfig(self.edges[self.selected]['condition_text_id'], text=new_condition, fill=condition_color)
                # Update the background rectangle to match new text size
                self.update_condition_bg(self.selected)
                condition_window.destroy()
            
            def cancel_condition():
                condition_window.destroy()
            
            ttk.Button(button_frame, text="Save", command=save_condition).pack(side="left", padx=4)
            ttk.Button(button_frame, text="Cancel", command=cancel_condition).pack(side="left", padx=4)

    def set_default_state(self):
        if self.selected and self.nodes[self.selected]['type'] == 'state':
            # Remove green outline from old default state
            if self.default_state is not None and self.default_state != self.selected:
                try:
                    self.canvas.itemconfig(self.default_state, outline="black", width=1)
                except tk.TclError:
                    pass
            # Set new default state
            self.default_state = self.selected
            # Apply green outline
            self.canvas.itemconfig(self.selected, outline="green", width=2)

    def update_condition_bg(self, edge_id):
        """Update the background rectangle of a condition to match the text size."""
        if edge_id in self.edges:
            condition_text_id = self.edges[edge_id]['condition_text_id']
            text_bbox = self.canvas.bbox(condition_text_id)
            if text_bbox:
                bg_id = self.edges[edge_id].get('condition_bg_id')
                if bg_id:
                    # Update existing background rectangle
                    self.canvas.coords(bg_id, 
                        text_bbox[0] - 3, text_bbox[1] - 3, 
                        text_bbox[2] + 3, text_bbox[3] + 3)
                else:
                    # Create background rectangle if it doesn't exist
                    bg_rect_id = self.canvas.create_rectangle(
                        text_bbox[0] - 3, text_bbox[1] - 3, 
                        text_bbox[2] + 3, text_bbox[3] + 3,
                        fill="#c0c0c0", outline="none", tags=("shape", "condition_bg")
                    )
                    self.canvas.tag_lower(bg_rect_id, condition_text_id)
                    self.edges[edge_id]['condition_bg_id'] = bg_rect_id

    def update_text(self, item_id):
        if 'text_id' in self.nodes[item_id]:
            self.canvas.delete(self.nodes[item_id]['text_id'])
        if 'text_outline_id' in self.nodes[item_id]:
            self.canvas.delete(self.nodes[item_id]['text_outline_id'])
        if 'code_id' in self.nodes[item_id]:
            self.canvas.delete(self.nodes[item_id]['code_id'])
        if 'code_outline_id' in self.nodes[item_id]:
            self.canvas.delete(self.nodes[item_id]['code_outline_id'])
        if self.nodes[item_id]['type'] == 'state':
            bbox = self.canvas.bbox(item_id)
            top_left_x = bbox[0] + 10
            top_left_y = bbox[1] + 10
            text_id = self.canvas.create_text(top_left_x, top_left_y, text=self.nodes[item_id]['name'], font=("Arial", 10), anchor="nw", tags=("shape", "text"))
            self.nodes[item_id]['text_id'] = text_id
            
            # Create a subtle outline around the text
            text_bbox = self.canvas.bbox(text_id)
            if text_bbox:
                outline_id = self.canvas.create_rectangle(
                    text_bbox[0] - 3, text_bbox[1] - 3, text_bbox[2] + 3, text_bbox[3] + 3,
                    outline="#e0e0e0", width=1, tags=("shape", "text_outline")
                )
                # Lower the outline behind the text
                self.canvas.tag_lower(outline_id, text_id)
                self.nodes[item_id]['text_outline_id'] = outline_id
            
            # Create code area below the name
            code_top_y = text_bbox[3] + 5 if text_bbox else top_left_y + 20
            code_left_x = bbox[0] + 10
            code_right_x = bbox[2] - 10
            code_bottom_y = bbox[3] - 10
            
            default_code = "// code executed once on entry of the state\nentry:\n\n// cyclic execution as long as state is active\nduring:\n\n// code executed when exiting the state\nexit:"
            
            # Use stored code or default
            code_text = self.nodes[item_id].get('code', default_code)
            
            code_id = self.canvas.create_text(
                code_left_x, code_top_y, 
                text=code_text, 
                font=("Courier", 8), 
                anchor="nw", 
                width=int(code_right_x - code_left_x),
                tags=("shape", "code")
            )
            self.nodes[item_id]['code_id'] = code_id
            if 'code' not in self.nodes[item_id]:
                self.nodes[item_id]['code'] = default_code
            
            # Create a subtle light green outline around the code area
            code_bbox = self.canvas.bbox(code_id)
            if code_bbox:
                code_outline_id = self.canvas.create_rectangle(
                    code_bbox[0] - 3, code_bbox[1] - 3, code_bbox[2] + 3, code_bbox[3] + 3,
                    outline="#d0e8d0", width=1, tags=("shape", "code_outline")
                )
                # Lower the outline behind the code
                self.canvas.tag_lower(code_outline_id, code_id)
                self.nodes[item_id]['code_outline_id'] = code_outline_id
            
            # Lower the code area behind the rectangle so clicks affect the state
            self.canvas.tag_lower(code_id, item_id)

    def show_connections(self):
        win = tk.Toplevel(self)
        win.title("Connections")
        tree = ttk.Treeview(win, columns=("From", "To", "Condition"), show="headings")
        tree.heading("From", text="From")
        tree.heading("To", text="To")
        tree.heading("Condition", text="Condition")
        tree.pack(fill="both", expand=True)
        
        # Build a map of edges by their start and end nodes
        edge_map = {}
        for edge_id in self.canvas.find_withtag("edge"):
            tags = self.canvas.gettags(edge_id)
            start_id = None
            end_id = None
            for tag in tags:
                if tag.startswith("start:"):
                    start_id = int(tag.split(":")[1])
                elif tag.startswith("end:"):
                    end_id = int(tag.split(":")[1])
            if start_id is not None and end_id is not None:
                if (start_id, end_id) not in edge_map:
                    edge_map[(start_id, end_id)] = []
                edge_map[(start_id, end_id)].append(edge_id)
        
        # Helper function to enumerate all paths through junctions
        def find_all_paths(current_node, visited_nodes=None, path_edges=None):
            """
            Recursively find all paths from current node to final states.
            Returns: list of (final_state_id, list_of_edge_ids_in_path)
            """
            if visited_nodes is None:
                visited_nodes = set()
            if path_edges is None:
                path_edges = []
            
            # Prevent infinite loops
            if current_node in visited_nodes:
                return []
            
            visited_nodes.add(current_node)
            
            # If current node is a state, return this complete path
            if self.nodes[current_node]['type'] == 'state':
                return [(current_node, path_edges)]
            
            # If current node is a junction, find all outgoing edges
            all_paths = []
            for (start, end), edge_ids in edge_map.items():
                if start == current_node:
                    # For each outgoing edge from this junction, continue tracing
                    for edge_id in edge_ids:
                        new_path_edges = path_edges + [edge_id]
                        paths = find_all_paths(end, visited_nodes.copy(), new_path_edges)
                        all_paths.extend(paths)
            
            return all_paths
        
        # Process all edges and build state-to-state connections
        processed_edge_ids = set()
        connections = {}  # (start_state, end_state) -> list of edge_id lists
        
        # For each edge in the graph
        for (start_id, end_id), edge_ids in edge_map.items():
            # If starting from a state
            if self.nodes[start_id]['type'] == 'state':
                # Trace all paths from the end node
                if self.nodes[end_id]['type'] == 'junction':
                    # Junction path
                    paths = find_all_paths(end_id)
                    for final_state, path_edges in paths:
                        # Combine this edge with path edges
                        all_path_edges = edge_ids + path_edges
                        key = (start_id, final_state)
                        if key not in connections:
                            connections[key] = []
                        connections[key].append(all_path_edges)
                else:
                    # Direct state-to-state
                    key = (start_id, end_id)
                    if key not in connections:
                        connections[key] = []
                    connections[key].append(edge_ids)
        
        # Display all unique connections
        for (start_id, end_id), all_edge_lists in connections.items():
            # For each unique path, display it with combined conditions
            for edge_list in all_edge_lists:
                conditions = []
                for edge_id in edge_list:
                    if edge_id in self.edges and 'condition' in self.edges[edge_id]:
                        cond = self.edges[edge_id]['condition']
                        if cond and not cond.startswith(("//", "#", "%")):
                            conditions.append(cond)
                
                # Combine all conditions with AND
                if conditions:
                    combined_condition = " AND ".join(f"({cond})" if " " in cond else cond for cond in conditions)
                else:
                    combined_condition = "//[condition]"
                
                from_name = self.nodes[start_id]['name']
                to_name = self.nodes[end_id]['name']
                tree.insert("", "end", values=(from_name, to_name, combined_condition))

    def set_language(self, language):
        """Set the code generation language."""
        self.language = language
        self.language_var.set(language)
        
    def show_generated_code(self):
        """Open a window showing the generated code."""
        show_code_editor(self, self.nodes, self.edges, self.default_state, self.language)

    def save_layout(self):
        file = fd.asksaveasfilename(defaultextension=".lyt", filetypes=[("Layout files", "*.lyt")])
        if file:
            root = ET.Element("layout")
            # Save language setting
            ET.SubElement(root, "language", value=self.language)
            # Save default state id
            if self.default_state is not None:
                ET.SubElement(root, "default_state", id=str(self.default_state))
            for item_id, data in self.nodes.items():
                node_elem = ET.SubElement(root, "node", id=str(item_id), x=str(data['position'][0]), y=str(data['position'][1]), w=str(data['size'][0]), h=str(data['size'][1]), type=data['type'], name=str(data['name']))
                # Save code for states
                if data['type'] == 'state' and 'code' in data:
                    code_elem = ET.SubElement(node_elem, "code")
                    code_elem.text = data['code']
            for edge_id in self.canvas.find_withtag("edge"):
                tags = self.canvas.gettags(edge_id)
                start_id = None
                end_id = None
                for tag in tags:
                    if tag.startswith("start:"):
                        start_id = tag.split(":")[1]
                    elif tag.startswith("end:"):
                        end_id = tag.split(":")[1]
                if start_id and end_id:
                    rel_start = self.nodes[int(start_id)]['outgoing_points'][edge_id]
                    rel_end = self.nodes[int(end_id)]['incoming_points'][edge_id]
                    edge_elem = ET.SubElement(root, "edge", start=start_id, end=end_id, start_rel_x=str(rel_start[0]), start_rel_y=str(rel_start[1]), end_rel_x=str(rel_end[0]), end_rel_y=str(rel_end[1]))
                    # Save condition if exists
                    if edge_id in self.edges and 'condition' in self.edges[edge_id]:
                        condition_elem = ET.SubElement(edge_elem, "condition")
                        condition_elem.text = self.edges[edge_id]['condition']
            tree = ET.ElementTree(root)
            tree.write(file)

    def open_layout(self):
        file = fd.askopenfilename(filetypes=[("Layout files", "*.lyt")])
        if file:
            self.canvas.delete("all")
            self.nodes.clear()
            self.default_state = None  # Reset default state
            tree = ET.parse(file)
            root = tree.getroot()
            saved_to_new = {}
            
            # Restore language setting
            language_elem = root.find("language")
            if language_elem is not None:
                self.language = language_elem.get("value", "python")
                self.language_var.set(self.language)
            
            # Restore default state id
            default_elem = root.find("default_state")
            default_state_id = int(default_elem.get("id")) if default_elem is not None else None
            
            for node_elem in root.findall("node"):
                item_id = int(node_elem.get("id"))
                x = float(node_elem.get("x"))
                y = float(node_elem.get("y"))
                w = float(node_elem.get("w"))
                h = float(node_elem.get("h"))
                typ = node_elem.get("type")
                name = node_elem.get("name", "")
                if typ in ("rect", "state"):
                    item = self.canvas.create_rectangle(x, y, x+w, y+h, outline="black", tags=("shape","node"))
                elif typ in ("oval", "junction"):
                    item = self.canvas.create_oval(x, y, x+w, y+h, outline="black", tags=("shape","node"))
                
                # Load saved code or use default
                code_elem = node_elem.find("code")
                if code_elem is not None and code_elem.text:
                    saved_code = code_elem.text
                else:
                    saved_code = "// code executed once on entry of the state\nentry:\n\n// cyclic execution as long as state is active\nduring:\n\n// code executed when exiting the state\nexit:" if typ in ("rect", "state") else ''
                
                self.nodes[item] = {
                    'position': (x, y),
                    'size': (w, h),
                    'type': 'state' if typ in ("rect", "state") else 'junction',
                    'name': name,
                    'code': saved_code,
                    'incoming': [],
                    'outgoing': [],
                    'incoming_points': {},
                    'outgoing_points': {}
                }
                saved_to_new[item_id] = item
                if self.nodes[item]['type'] == 'state':
                    self.update_text(item)
            
            # Apply green outline to default state
            if default_state_id is not None and default_state_id in saved_to_new:
                self.default_state = saved_to_new[default_state_id]
                self.canvas.itemconfig(self.default_state, outline="green", width=2)
            
            for edge_elem in root.findall("edge"):
                start_id = int(edge_elem.get("start"))
                end_id = int(edge_elem.get("end"))
                rel_start_x = float(edge_elem.get("start_rel_x"))
                rel_start_y = float(edge_elem.get("start_rel_y"))
                rel_end_x = float(edge_elem.get("end_rel_x"))
                rel_end_y = float(edge_elem.get("end_rel_y"))
                # Calculate absolute positions
                actual_start = saved_to_new[start_id]
                actual_end = saved_to_new[end_id]
                bbox_start = self.canvas.bbox(actual_start)
                abs_start_x = bbox_start[0] + rel_start_x * (bbox_start[2] - bbox_start[0])
                abs_start_y = bbox_start[1] + rel_start_y * (bbox_start[3] - bbox_start[1])
                bbox_end = self.canvas.bbox(actual_end)
                abs_end_x = bbox_end[0] + rel_end_x * (bbox_end[2] - bbox_end[0])
                abs_end_y = bbox_end[1] + rel_end_y * (bbox_end[3] - bbox_end[1])
                edge_id = self.canvas.create_line(abs_start_x, abs_start_y, abs_end_x, abs_end_y, fill="black", width=2, arrow="last", tags=("shape","edge", f"start:{actual_start}", f"end:{actual_end}"))
                self.nodes[actual_start]['outgoing'].append(edge_id)
                self.nodes[actual_end]['incoming'].append(edge_id)
                self.nodes[actual_start]['outgoing_points'][edge_id] = (rel_start_x, rel_start_y)
                self.nodes[actual_end]['incoming_points'][edge_id] = (rel_end_x, rel_end_y)
                
                # Restore condition if it exists
                condition_elem = edge_elem.find("condition")
                condition_text = condition_elem.text if condition_elem is not None and condition_elem.text else "//[condition]"
                
                # Create condition text at midpoint
                mid_x = (abs_start_x + abs_end_x) / 2
                mid_y = (abs_start_y + abs_end_y) / 2
                
                condition_color = self.get_condition_text_color(condition_text)
                condition_text_id = self.canvas.create_text(mid_x, mid_y, text=condition_text, font=("Courier", 9), fill=condition_color, tags=("shape", "condition", f"condition_of:{edge_id}"))
                
                # Create gray background rectangle for the text
                text_bbox = self.canvas.bbox(condition_text_id)
                bg_rect_id = None
                if text_bbox:
                    bg_rect_id = self.canvas.create_rectangle(
                        text_bbox[0] - 3, text_bbox[1] - 3, text_bbox[2] + 3, text_bbox[3] + 3,
                        fill="#e9e9e9", outline="#849eaf", tags=("shape", "condition_bg")
                    )
                    # Lower the rectangle behind the text
                    self.canvas.tag_lower(bg_rect_id, condition_text_id)
                
                # Store edge data
                self.edges[edge_id] = {
                    'condition': condition_text,
                    'condition_text_id': condition_text_id,
                    'condition_bg_id': bg_rect_id,
                    'start_pos': (abs_start_x, abs_start_y),
                    'end_pos': (abs_end_x, abs_end_y)
                }

if __name__ == "__main__":
    app = GraphicalMaster()
    app.mainloop()