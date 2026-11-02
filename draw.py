"""Tkinter drawing window. main.py uses Save & Print; standalone use saves only."""

from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk


def run(print_on_save=False):
    base = Path(__file__).resolve().parent
    points = []
    saved_path = None
    root = tk.Tk()
    root.title('Nutella Printer - Drawing App')
    window_w, window_h = (1180, 780)
    screen_w, screen_h = (root.winfo_screenwidth(), root.winfo_screenheight())
    root.geometry('{}x{}+{}+{}'.format(window_w, window_h, max(0, (screen_w-window_w)//2), max(0, (screen_h-window_h)//2)))
    root.minsize(980, 700)
    mode = {'value': 'draw', 'travel_next': False}
    shell = tk.Frame(root, bg='#f7f7f8')
    shell.pack(expand=True, fill='both')
    sidebar = tk.Frame(shell, width=250, bg='#f0f0f2', padx=14, pady=16)
    sidebar.pack(side='left', fill='y')
    sidebar.pack_propagate(False)
    tk.Label(sidebar, text='Your drawings', font=('Segoe UI', 15, 'bold'), bg='#f0f0f2').pack(anchor='w', pady=(0, 12))
    tk.Button(sidebar, text='+  New Drawing', font=('Segoe UI', 11, 'bold'), command=lambda: clear()).pack(fill='x', pady=(0, 16))
    tk.Label(sidebar, text='PREVIOUS DESIGNS', font=('Segoe UI', 9, 'bold'), fg='#666', bg='#f0f0f2').pack(anchor='w', pady=(0, 6))
    design_list = tk.Listbox(sidebar, relief='flat', font=('Segoe UI', 11), activestyle='none', exportselection=False)
    design_list.pack(fill='both', expand=True)
    tk.Button(sidebar, text='Open selected', command=lambda: load_design()).pack(fill='x', pady=(10, 0))

    content = tk.Frame(shell, bg='#f7f7f8')
    content.pack(side='left', expand=True, fill='both')
    controls_top = tk.Frame(content, bg='#f7f7f8')
    controls_top.pack(pady=14)
    canvas = tk.Canvas(content, width=600, height=600, bg='white', highlightthickness=1, highlightbackground='#ddd')
    canvas.pack(expand=True)
    status = tk.Label(content, text='', wraplength=760, bg='#f7f7f8', fg='#444')
    status.pack(pady=8)
    controls = tk.Frame(content, bg='#f7f7f8')
    controls.pack(pady=(0, 12))
    tk.Button(controls_top, text='Draw', command=lambda: set_draw_mode()).pack(side='left', padx=5)
    tk.Button(controls_top, text='New Stroke', command=lambda: set_stroke_mode()).pack(side='left', padx=5)
    tk.Button(controls, text='Clear', command=lambda: clear()).pack(side='left', padx=5)
    tk.Button(controls, text='Save & Print' if print_on_save else 'Save', command=lambda: save()).pack(side='left', padx=5)

    def set_draw_mode():
        mode['value'] = 'draw'
        mode['travel_next'] = False
        status.config(text='Drawing mode')

    def set_stroke_mode():
        mode['value'] = 'stroke'
        mode['travel_next'] = True
        status.config(text='Click or drag to place the next stroke start')

    def point(event):
        # Original normalized coordinates and flipped Y; bound to the canvas.
        return (min(1, max(0, event.x/max(1, canvas.winfo_width()))),
                min(1, max(0, 1-event.y/max(1, canvas.winfo_height()))))

    def draw(event):
        if mode['travel_next']:
            x, y = point(event)
            points.append((x, y, False))
            canvas.create_rectangle(event.x-3, event.y-3, event.x+3, event.y+3,
                                    outline='red', tags='marks')
            mode['travel_next'] = False
            mode['value'] = 'draw'
            status.config(text='Drawing')
            return
        x, y = point(event)
        points.append((x, y, True))
        canvas.create_oval(event.x-2, event.y-2, event.x+2, event.y+2,
                           fill='black', tags='marks')

    def travel(event):
        x, y = point(event)
        points.append((x, y, False))
        canvas.create_rectangle(event.x-3, event.y-3, event.x+3, event.y+3,
                                outline='red', tags='marks')

    def clear():
        points.clear()
        canvas.delete('marks')
        status.config(text='')

    def save():
        nonlocal saved_path
        if len(points) < 2 or points[0][2]:
            status.config(text='Add at least two drawing points before saving.')
            return
        paths = base/'paths'
        paths.mkdir(exist_ok=True)
        numbers = [int(p.stem) for p in paths.glob('*.txt') if p.stem.isdigit()]
        destination = paths/'{}.txt'.format(max(numbers)+1 if numbers else 0)
        destination.write_text(''.join('{:.4f},{:.4f},{}\n'.format(x, y, int(d))
                                      for x, y, d in points), encoding='utf-8')
        saved_path = destination
        print('Saved {} points to {}'.format(len(points), destination), flush=True)
        root.destroy()

    try:
        bread_image = Image.open(base/'bread.png').resize((600, 600))
        bread_tk = ImageTk.PhotoImage(bread_image)
        canvas.create_image(0, 0, anchor='nw', image=bread_tk)
    except FileNotFoundError:
        status.config(text='Bread background not found; drawing still works.')
    canvas.bind('<B1-Motion>', draw)

    def refresh_designs():
        design_list.delete(0, tk.END)
        paths = base/'paths'
        files = sorted((f for f in paths.glob('*.txt') if f.stem.isdigit()), key=lambda f: int(f.stem), reverse=True)
        for path in files:
            design_list.insert(tk.END, 'Drawing {}'.format(path.stem))

    def load_design():
        selection = design_list.curselection()
        if not selection:
            status.config(text='Select a previous drawing first.')
            return
        files = sorted((f for f in (base/'paths').glob('*.txt') if f.stem.isdigit()), key=lambda f: int(f.stem), reverse=True)
        source = files[selection[0]]
        clear()
        try:
            for line in source.read_text(encoding='utf-8').splitlines():
                x, y, drawing = line.split(',')
                item = (float(x), float(y), bool(int(drawing)))
                points.append(item)
                px = item[0]*canvas.winfo_width()
                py = (1-item[1])*canvas.winfo_height()
                if item[2]:
                    canvas.create_oval(px-2, py-2, px+2, py+2, fill='black', tags='marks')
                else:
                    canvas.create_rectangle(px-3, py-3, px+3, py+3, outline='red', tags='marks')
            status.config(text='Loaded Drawing {} ({} points)'.format(source.stem, len(points)))
        except (OSError, ValueError) as error:
            status.config(text='Could not load design: {}'.format(error))

    refresh_designs()
    root.mainloop()
    return saved_path


if __name__ == '__main__':
    run()
