import tkinter as tk
import os

points = []

def draw(event):
    """Left-drag = drawing (printing enabled)."""
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    
    norm_x = event.x / w
    norm_y = 1 - (event.y / h)  # flip y
    
    points.append((norm_x, norm_y, True))  # printing = True
    r = 2
    canvas.create_oval(event.x-r, event.y-r, event.x+r, event.y+r, fill="black")

def move_without_print(event):
    """Right-click = jump/move (printing disabled)."""
    w = canvas.winfo_width()
    h = canvas.winfo_height()

    norm_x = event.x / w
    norm_y = 1 - (event.y / h)

    points.append((norm_x, norm_y, False))  # printing = False
    r = 3
    canvas.create_rectangle(event.x-r, event.y-r, event.x+r, event.y+r, outline="red")

def save_points():
    os.makedirs("paths", exist_ok=True)

    # find next available number
    existing = [int(f.split(".")[0]) for f in os.listdir("paths") if f.endswith(".txt")]
    next_num = max(existing)+1 if existing else 0

    filepath = f"paths/{next_num}.txt"
    with open(filepath, "w") as f:
        for p in points:
            f.write(f"{p[0]:.4f},{p[1]:.4f},{int(p[2])}\n")

    print(f"Saved {len(points)} points to {filepath}")
    root.destroy()

root = tk.Tk()
root.title("Draw Path - Start any Sequence w/ Right Press!")

canvas = tk.Canvas(root, width=400, height=400, bg="white")
canvas.pack()

# Bind left drag for drawing, right click for move-only
canvas.bind("<B1-Motion>", draw)
canvas.bind("<Button-3>", move_without_print)

btn = tk.Button(root, text="Save", command=save_points)
btn.pack()

root.mainloop()
