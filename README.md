# EV3 Nutella Printer

This project uses a laptop and a LEGO EV3 robot to draw with Nutella. Drawings are saved in `paths/`.

Install the packages in `requirements.txt`, connect the EV3, then run:

```bash
python main.py
```

This prints the latest saved drawing. To open the drawing editor, run `python main.py --draw`.

The laptop connects to the EV3 over SSH. Check the wiring and watch the printer while it runs. The software cannot detect whether Nutella is flowing or whether the syringe has reached its limit.
